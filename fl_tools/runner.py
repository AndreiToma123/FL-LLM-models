"""Run SoapFL over a list of Defects4J bugs: resumable, with per-bug logs and timeouts.

Safety rules baked in (all learned from reading SoapFL's code):

* SoapFL caches every LLM answer ("checkpoint") inside the bug's output directory
  and silently reuses it on the next run. Re-using an output directory after
  changing the model, prompt config or parsing mode would therefore mix results of
  different experiments. Each run gets its own directory, and ``run_meta.json``
  makes the runner refuse to resume it with different settings.
* A bug counts as finished only when ``result.json`` exists (that is SoapFL's own
  rule), so a crashed bug is retried from its checkpoints on the next invocation.
* ``PYTHONHASHSEED=0`` and ``SOAPFL_SEED`` make the set-ordering and the random
  test-suite sampling in SoapFL deterministic for a given bug.
"""
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from .bugs import VERSION, Bug, dataset_of_version
from .bugs import defects4j_home as dataset_defects4j_home
from .results import snapshot_ground_truth

# (class, regex searched in the tail of the run log), first match wins
FAILURE_PATTERNS = [
    ("context_overflow_server", r"maximum context length|context_length_exceeded|context length exceeded|reduce the length of the messages"),
    ("context_overflow_guard", r"max_tokens_exceeded_by_camel"),
    ("score_parse", r"Invalid Method Review Conclusion"),
    ("no_failing_test_output", r"parse_test_report|failing_tests"),
    ("auth_error", r"AuthenticationError|invalid_api_key|Incorrect API key"),
    ("model_not_found", r"(?<![A-Za-z])NotFoundError|model .{0,80} does not exist"),   # not FileNotFoundError
    ("rate_limited", r"RateLimitError"),
    ("server_unreachable", r"APIConnectionError|APITimeoutError|Connection error|Connection refused|Max retries exceeded|Read timed out"),
    ("defects4j_missing", r"No such file or directory: 'defects4j'|defects4j: (command )?not found"),
    ("local_model_name_missing", r"SOAPFL_MODEL_NAME"),
]
# A bug that hits the per-bug time limit is NOT retried: the second attempt makes the same model calls and times out
# again (HypoDeduce on CSC, 2026-11-01: Closure bugs ran 3 h + 3 h while the rest of the GPU sat idle).
RETRYABLE = {"server_unreachable", "rate_limited", "killed_oom"}
# Failures that are part of the benchmark setup, not a broken run (Defects4J gives no failing-test output for some
# Mockito bugs in our container in every pipeline): they do not count for the circuit breaker.
EXPECTED_FAILURES = {"no_failing_test_output"}
# A finished bug's last status that a resumed run does NOT try again unless retry_failed is set: the bug simply did
# not work in this run (reported like the other papers do). Retryable infrastructure errors are always retried.
FINAL_STATUSES = {"failed", "timeout", "no_result", "runner_error"}

# settings that must not change when a run directory is resumed
META_GUARDED_ENV = ["SOAPFL_MODEL_NAME", "SOAPFL_CONTEXT_LIMIT", "SOAPFL_EXTRA_BODY", "SOAPFL_STRIP_THINK",
                    "SOAPFL_MAX_COMPLETION_TOKENS", "SOAPFL_TOKEN_MARGIN",
                    "SOAPFL_HD_HYPOTHESES", "SOAPFL_HD_CLASSES", "SOAPFL_HD_METHODS", "SOAPFL_HD_SELECTION",
                    "SOAPFL_CA_MODE", "SOAPFL_CA_K"]
PIPELINES = ("soapfl", "hypodeduce", "classaug")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def classify_failure(log_text: str, tail_chars: int = 20000) -> str:
    tail = log_text[-tail_chars:]
    for name, pattern in FAILURE_PATTERNS:
        if re.search(pattern, tail):
            return name
    return "other"


def last_error_line(log_text: str) -> str:
    for line in reversed(log_text.strip().splitlines()):
        if re.match(r"^\s*[\w.]*(Error|Exception|Exit)\b", line) or "Traceback" in line:
            return line.strip()[:300]
    return ""


def soapfl_commit(soapfl_dir: str) -> str:
    try:
        out = subprocess.run(["git", "-C", soapfl_dir, "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def patch_digest(patches_dir: str) -> str:
    h = hashlib.sha256()
    if os.path.isdir(patches_dir):
        for name in sorted(os.listdir(patches_dir)):
            if name.endswith(".patch"):
                with open(os.path.join(patches_dir, name), "rb") as f:
                    h.update(f.read())
    return h.hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_meta(name: str, soapfl_dir: str, config: str, model: str, lenient: bool, seed: int,
               patches_dir: str, pipeline: str = "soapfl") -> dict:
    llm_env = {k: v for k, v in os.environ.items()
               if k.startswith("SOAPFL_") and "KEY" not in k and k not in ("SOAPFL_UDS", "SOAPFL_HD_CONFIG_DIR")}
    meta = {
        "name": name,
        "pipeline": pipeline,
        "created": _utc_now(),
        "soapfl_commit": soapfl_commit(soapfl_dir),
        "patch_digest": patch_digest(patches_dir),
        "config": config,
        "model_type": model,
        "lenient": lenient,
        "seed": seed,
        "llm_env": llm_env,
        "python": sys.version.split()[0],
        "host": platform.node(),
    }
    if pipeline == "hypodeduce":
        from .hypodeduce.config import prompts_digest
        meta["hypodeduce_prompts_digest"] = prompts_digest()
    if pipeline == "classaug":
        import hashlib
        with open(os.path.join(REPO_ROOT, "fl_tools", "classaug.py"), "rb") as f:
            meta["classaug_digest"] = hashlib.sha256(f.read()).hexdigest()[:16]
    return meta


class MetaMismatch(RuntimeError):
    pass


def check_or_write_meta(out_dir: str, meta: dict, allow_change: bool = False) -> dict:
    path = os.path.join(out_dir, "run_meta.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return meta
    with open(path, "r", encoding="utf-8") as f:
        old = json.load(f)
    problems = []
    for key in ("config", "model_type", "lenient", "seed"):
        if old.get(key) != meta.get(key):
            problems.append(f"{key}: was {old.get(key)!r}, now {meta.get(key)!r}")
    for key, default in (("pipeline", "soapfl"), ("hypodeduce_prompts_digest", None), ("dataset", None),
                         ("classaug_digest", None)):
        if old.get(key, default) != meta.get(key, default):
            problems.append(f"{key}: was {old.get(key, default)!r}, now {meta.get(key, default)!r}")
    for key in META_GUARDED_ENV:
        a, b = old.get("llm_env", {}).get(key), meta.get("llm_env", {}).get(key)
        if a != b:
            problems.append(f"{key}: was {a!r}, now {b!r}")
    if problems and not allow_change:
        raise MetaMismatch(
            f"{out_dir} was created with different settings:\n  " + "\n  ".join(problems) +
            "\nSoapFL reuses cached LLM answers stored in that directory, so mixing settings would "
            "silently contaminate the results. Use a new --name (or --allow-meta-change if you are "
            "sure).")
    return old


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:  # pragma: no cover
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass


class Runner:
    def __init__(self, *, name: str, results_dir: str, soapfl_dir: str, config: str = "Default",
                 model: str = "LOCAL", lenient: bool = True, seed: int = 0, jobs: int = 1,
                 timeout: int = 3600, retries: int = 1, python: Optional[str] = None,
                 defects4j_home: Optional[str] = None, patches_dir: Optional[str] = None,
                 allow_meta_change: bool = False, heartbeat: float = 60.0, progress: Callable[[str], None] = print,
                 pipeline: str = "soapfl", retry_failed: bool = False, tail_factor: float = 3.0,
                 tail_min: int = 600, breaker_rate: float = 0.5, breaker_min: int = 30):
        if pipeline not in PIPELINES:
            raise ValueError(f"unknown pipeline {pipeline!r}; use one of {PIPELINES}")
        self.pipeline = pipeline
        self.name = name
        self.out_dir = os.path.abspath(os.path.join(results_dir, name))
        self.soapfl_dir = os.path.abspath(soapfl_dir)
        self.config, self.model, self.lenient, self.seed = config, model, lenient, seed
        self.jobs, self.timeout, self.retries = max(1, jobs), timeout, retries
        self.python = python or sys.executable
        self.defects4j_home_override = defects4j_home       # explicit --defects4j-home wins for every bug
        self.defects4j_home = defects4j_home or os.environ.get("DEFECTS4J_HOME")
        self.patches_dir = patches_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "patches")
        self.allow_meta_change = allow_meta_change
        self.heartbeat = heartbeat
        self.progress = progress
        self._lock = threading.Lock()
        self._procs: List[subprocess.Popen] = []
        self._stopping = threading.Event()   # set on Ctrl-C / SIGTERM: no new attempts, no retries
        # --- GPU-budget safeguards (2026-11-02: one hung bug held a whole GPU for 6 h) ---
        # retry_failed: a resumed run also re-runs bugs whose last attempt failed for good (default: skip them)
        # tail guard: once every bug has started, a still-running bug is stopped after
        #   max(tail_min, tail_factor x the 95th percentile of finished bugs' run time) (0 = off)
        # circuit breaker: after breaker_min finished attempts, stop the whole run if more than breaker_rate of them
        #   failed (expected benchmark failures excluded): something is broken, do not burn the budget (0 = off)
        self.retry_failed = retry_failed
        self.tail_factor, self.tail_min = tail_factor, tail_min
        self.breaker_rate, self.breaker_min = breaker_rate, breaker_min
        self._pending = 0                    # bugs not yet started
        self._ok_walls: List[float] = []     # run times of successful attempts (incl. earlier jobs of this run)
        self._finished = 0                   # attempts finished in this job
        self._bad = 0                        # ... of which unexpected failures
        self.breaker_tripped = ""

    # ---------------------------------------------------------------- helpers
    def bug_dir(self, bug: Bug) -> str:
        return os.path.join(self.out_dir, bug.dirname)

    def is_finished(self, bug: Bug) -> bool:
        return os.path.exists(os.path.join(self.bug_dir(bug), "result.json"))

    def _env(self, bug: Bug) -> dict:
        env = os.environ.copy()
        env.update({
            "SOAPFL_RUN_DIR": self.bug_dir(bug),
            "SOAPFL_SEED": str(self.seed),
            "SOAPFL_LENIENT_PARSING": "1" if self.lenient else "0",
            "PYTHONHASHSEED": "0",
            "PYTHONUNBUFFERED": "1",
        })
        home = self.defects4j_home_for(bug)
        if home:
            env["PATH"] = os.path.join(home, "framework", "bin") + os.pathsep + env.get("PATH", "")
            env["DEFECTS4J_HOME"] = home
        if self.pipeline == "hypodeduce":
            env["PYTHONPATH"] = REPO_ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            env["SOAPFL_HD_CONFIG_DIR"] = os.path.join(self.out_dir, "_hypodeduce_config")
        if self.pipeline == "classaug":
            # the bug's free class ranking from its failure context (no context = plain SoapFL for this bug)
            from .classaug import ENV_RANKING, rank_classes
            from .context import load_context
            env["PYTHONPATH"] = REPO_ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            ctx = load_context(os.environ.get("SOAPFL_CA_CONTEXT"), bug.dirname)
            env[ENV_RANKING] = json.dumps(rank_classes(ctx)[:20])
            env["SOAPFL_DIR"] = self.soapfl_dir
            env["SOAPFL_DIR"] = self.soapfl_dir
        return env

    def defects4j_home_for(self, bug: Bug) -> Optional[str]:
        """Dataset 1 uses DEFECTS4J_HOME as before; dataset 2 (Defects4J 2.0) its own installation."""
        if self.defects4j_home_override:
            return self.defects4j_home_override
        if bug.version == VERSION:
            return self.defects4j_home
        return dataset_defects4j_home(bug.version)

    def _limit(self) -> float:
        """Current time limit per attempt (seconds; 0 = none): the fixed timeout, shortened in the tail."""
        limit = float(self.timeout) if self.timeout > 0 else 0.0
        with self._lock:
            tail = self._pending == 0 and self.tail_factor > 0 and len(self._ok_walls) >= 10
            walls = sorted(self._ok_walls) if tail else []
        if tail:
            p95 = walls[min(len(walls) - 1, int(0.95 * len(walls)))]
            t = max(float(self.tail_min), self.tail_factor * p95)
            limit = min(limit, t) if limit else t
        return limit

    def _previous_rows(self) -> Dict[str, dict]:
        last: Dict[str, dict] = {}
        try:
            with open(os.path.join(self.out_dir, "runs.jsonl"), "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            row = json.loads(line)
                        except ValueError:
                            continue
                        last[row.get("bug")] = row
                        if row.get("status") == "ok" and row.get("wall_s"):
                            self._ok_walls.append(float(row["wall_s"]))
        except OSError:
            pass
        return last

    def _command(self, bug: Bug) -> List[str]:
        entry = {"hypodeduce": ["-m", "fl_tools.hypodeduce.soapfl_entry"],
                 "classaug": ["-m", "fl_tools.classaug"]}.get(self.pipeline, ["run.py"])
        return [self.python, *entry, "--config", self.config, "--version", bug.version,
                "--project", bug.project, "--bugID", str(bug.id), "--output", self.out_dir,
                "--model", self.model]

    def _append_run(self, row: dict) -> None:
        with self._lock, open(os.path.join(self.out_dir, "runs.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    # ----------------------------------------------------------------- one bug
    def _heartbeat(self, bug: Bug, started: float) -> None:
        calls = 0
        path = os.path.join(self.bug_dir(bug), "events.jsonl")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                calls = sum(1 for line in f if '"llm_call"' in line)
        except OSError:
            pass
        self.progress(f"  ... {bug.name} still running: {(time.time() - started) / 60:.0f} min, "
                      f"{calls} model calls so far")

    def _spawn(self, bug: Bug, attempt: int) -> dict:
        log_dir = os.path.join(self.out_dir, "_logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{bug.name}.log")
        started = time.time()
        status, returncode = "failed", None
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"\n===== attempt {attempt} at {_utc_now()} =====\n")
            log.flush()
            proc = subprocess.Popen(self._command(bug), cwd=self.soapfl_dir, env=self._env(bug),
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            with self._lock:
                self._procs.append(proc)
                if self._stopping.is_set():      # stop requested while this bug was starting
                    _kill_group(proc)
            tail_cut = False
            try:
                while True:
                    try:
                        limit = self._limit()
                        remaining = limit - (time.time() - started) if limit > 0 else self.heartbeat
                        returncode = proc.wait(timeout=max(0.1, min(self.heartbeat, remaining)))
                        break
                    except subprocess.TimeoutExpired:
                        limit = self._limit()
                        if limit > 0 and time.time() - started >= limit:
                            tail_cut = self.timeout <= 0 or limit < self.timeout
                            _kill_group(proc)
                            proc.wait()
                            status = "timeout"
                            break
                        self._heartbeat(bug, started)
            finally:
                with self._lock:
                    if proc in self._procs:
                        self._procs.remove(proc)
        wall = time.time() - started

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        # only classify the log of this attempt
        text = text.split(f"===== attempt {attempt} at")[-1]

        error_class = ""
        if status == "timeout":
            error_class = "tail_timeout" if tail_cut else "timeout"
        elif self.is_finished(bug):
            status = "ok"
        elif returncode == 0:
            status = "no_result"
        else:
            status = "failed"
            error_class = classify_failure(text)
            if returncode in (-9, 137) and error_class == "other":
                error_class = "killed_oom"   # SIGKILL: usually Docker/WSL ran out of memory (too many --jobs?)
        row = {"bug": bug.name, "status": status, "returncode": returncode, "attempt": attempt,
               "wall_s": round(wall, 1), "error_class": error_class,
               "error_line": last_error_line(text) if status in ("failed", "timeout") else "",
               "finished_at": _utc_now()}
        return row

    def run_bug(self, bug: Bug) -> dict:
        row: dict = {}
        with self._lock:
            self._pending -= 1
        for attempt in range(1, self.retries + 2):
            if self._stopping.is_set():
                break
            row = self._spawn(bug, attempt)
            if self._stopping.is_set() and row["status"] != "ok":
                row.update(status="interrupted", error_class="interrupted")
            self._append_run(row)
            self._account(row)
            bug_dir = self.bug_dir(bug)
            if os.path.isdir(bug_dir):
                snapshot_ground_truth(self.soapfl_dir, bug_dir, self.python)
            if row["status"] in ("ok", "no_result", "interrupted") or row["error_class"] not in RETRYABLE:
                break
        return row or {"bug": bug.name, "status": "interrupted", "error_class": "interrupted", "wall_s": 0}

    def _account(self, row: dict) -> None:
        """Record a finished attempt for the tail guard and the circuit breaker."""
        trip = ""
        with self._lock:
            if row["status"] == "ok":
                self._ok_walls.append(float(row.get("wall_s") or 0))
            if row["status"] == "interrupted":
                return
            self._finished += 1
            if row["status"] != "ok" and row.get("error_class") not in EXPECTED_FAILURES:
                self._bad += 1
            if (self.breaker_rate > 0 and not self.breaker_tripped and self._finished >= self.breaker_min
                    and self._bad > self.breaker_rate * self._finished):
                trip = self.breaker_tripped = (
                    f"circuit breaker: {self._bad} of the {self._finished} finished attempts failed "
                    f"(more than {self.breaker_rate:.0%}); stopping the run so the GPU budget is not spent on a "
                    f"broken setup. Check the logs, fix, and re-submit (add --retry-failed to re-run the failed bugs).")
        if trip:
            self.progress("!!! " + trip)
            self.stop()

    def stop(self) -> None:
        """Stop starting new bugs and kill the running ones (their rows are written as interrupted)."""
        self._stopping.set()
        with self._lock:
            for proc in list(self._procs):
                _kill_group(proc)

    # ------------------------------------------------------------------ batch
    def run(self, bugs: List[Bug]) -> dict:
        versions = sorted({b.version for b in bugs})
        if len(versions) > 1:
            raise ValueError(f"one run must stay within one dataset; got Defects4J versions {versions}")
        os.makedirs(self.out_dir, exist_ok=True)
        meta = build_meta(self.name, self.soapfl_dir, self.config, self.model, self.lenient, self.seed,
                          self.patches_dir, self.pipeline)
        if versions and versions[0] != VERSION:     # dataset 1 runs keep their old metadata unchanged
            meta["dataset"] = dataset_of_version(versions[0])
            meta["defects4j_version"] = versions[0]
        check_or_write_meta(self.out_dir, meta, self.allow_meta_change)
        if self.pipeline == "hypodeduce":
            # the exact chain and prompts used, kept with the results (written once, before the workers start)
            from .hypodeduce.config import build_configs
            build_configs(self.soapfl_dir, os.path.join(self.out_dir, "_hypodeduce_config"))

        previous = self._previous_rows()
        todo = [b for b in bugs if not self.is_finished(b)]
        skipped = len(bugs) - len(todo)
        given_up = []
        if not self.retry_failed:
            given_up = [b for b in todo if previous.get(b.name, {}).get("status") in FINAL_STATUSES
                        and previous[b.name].get("error_class") not in RETRYABLE]
            todo = [b for b in todo if b not in given_up]
        self._pending = len(todo)
        self.progress(f"{len(bugs)} bugs selected, {skipped} already finished, "
                      + (f"{len(given_up)} failed in an earlier job and skipped (use --retry-failed to re-run them), "
                         if given_up else "")
                      + f"{len(todo)} to run ({self.jobs} parallel, timeout {self.timeout}s, tail guard "
                      + (f"{self.tail_factor:g} x p95 >= {self.tail_min}s" if self.tail_factor > 0 else "off")
                      + ", circuit breaker "
                      + (f"> {self.breaker_rate:.0%} failures after {self.breaker_min}" if self.breaker_rate > 0 else "off")
                      + f") -> {self.out_dir}")

        results: List[dict] = []
        done = 0
        started = time.time()
        pool = ThreadPoolExecutor(max_workers=self.jobs)
        try:
            futures = {pool.submit(self.run_bug, b): b for b in todo}
            for future in as_completed(futures):
                bug = futures[future]
                try:
                    row = future.result()
                except Exception as exc:  # a bug in the runner itself must not stop the batch
                    row = {"bug": bug.name, "status": "runner_error", "error_class": type(exc).__name__,
                           "error_line": str(exc)[:300], "wall_s": 0}
                    self._append_run(row)
                results.append(row)
                done += 1
                elapsed = time.time() - started
                eta = elapsed / done * (len(todo) - done)
                detail = f" [{row['error_class']}]" if row.get("error_class") else ""
                self.progress(f"[{done}/{len(todo)}] {bug.name}: {row['status']}{detail} "
                              f"({row.get('wall_s', 0):.0f}s, ETA {eta / 60:.0f} min)")
        except KeyboardInterrupt:
            self.progress("interrupted: stopping running SoapFL processes (progress is resumable)")
            self._stopping.set()
            for future in list(futures):
                future.cancel()
            with self._lock:
                for proc in list(self._procs):
                    _kill_group(proc)
            raise
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        counts: Dict[str, int] = {}
        for row in results:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {"selected": len(bugs), "skipped_finished": skipped, "skipped_failed": len(given_up),
                "ran": len(todo), "status_counts": counts, "out_dir": self.out_dir,
                "circuit_breaker": self.breaker_tripped}
