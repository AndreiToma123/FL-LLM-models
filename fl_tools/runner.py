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

from .bugs import VERSION, Bug
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
RETRYABLE = {"server_unreachable", "rate_limited", "timeout", "killed_oom"}

# settings that must not change when a run directory is resumed
META_GUARDED_ENV = ["SOAPFL_MODEL_NAME", "SOAPFL_CONTEXT_LIMIT", "SOAPFL_EXTRA_BODY", "SOAPFL_STRIP_THINK",
                    "SOAPFL_MAX_COMPLETION_TOKENS", "SOAPFL_TOKEN_MARGIN",
                    "SOAPFL_HD_HYPOTHESES", "SOAPFL_HD_CLASSES", "SOAPFL_HD_METHODS", "SOAPFL_HD_SELECTION"]
PIPELINES = ("soapfl", "hypodeduce")
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
    for key, default in (("pipeline", "soapfl"), ("hypodeduce_prompts_digest", None)):
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
                 pipeline: str = "soapfl"):
        if pipeline not in PIPELINES:
            raise ValueError(f"unknown pipeline {pipeline!r}; use one of {PIPELINES}")
        self.pipeline = pipeline
        self.name = name
        self.out_dir = os.path.abspath(os.path.join(results_dir, name))
        self.soapfl_dir = os.path.abspath(soapfl_dir)
        self.config, self.model, self.lenient, self.seed = config, model, lenient, seed
        self.jobs, self.timeout, self.retries = max(1, jobs), timeout, retries
        self.python = python or sys.executable
        self.defects4j_home = defects4j_home or os.environ.get("DEFECTS4J_HOME")
        self.patches_dir = patches_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "patches")
        self.allow_meta_change = allow_meta_change
        self.heartbeat = heartbeat
        self.progress = progress
        self._lock = threading.Lock()
        self._procs: List[subprocess.Popen] = []
        self._stopping = threading.Event()   # set on Ctrl-C / SIGTERM: no new attempts, no retries

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
        if self.defects4j_home:
            env["PATH"] = os.path.join(self.defects4j_home, "framework", "bin") + os.pathsep + env.get("PATH", "")
        if self.pipeline == "hypodeduce":
            env["PYTHONPATH"] = REPO_ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            env["SOAPFL_HD_CONFIG_DIR"] = os.path.join(self.out_dir, "_hypodeduce_config")
            env["SOAPFL_DIR"] = self.soapfl_dir
        return env

    def _command(self, bug: Bug) -> List[str]:
        entry = ["-m", "fl_tools.hypodeduce.soapfl_entry"] if self.pipeline == "hypodeduce" else ["run.py"]
        return [self.python, *entry, "--config", self.config, "--version", VERSION,
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
            try:
                while True:
                    try:
                        remaining = self.timeout - (time.time() - started) if self.timeout > 0 else self.heartbeat
                        returncode = proc.wait(timeout=max(0.1, min(self.heartbeat, remaining)))
                        break
                    except subprocess.TimeoutExpired:
                        if self.timeout > 0 and time.time() - started >= self.timeout:
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
            error_class = "timeout"
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
        for attempt in range(1, self.retries + 2):
            if self._stopping.is_set():
                break
            row = self._spawn(bug, attempt)
            if self._stopping.is_set() and row["status"] != "ok":
                row.update(status="interrupted", error_class="interrupted")
            self._append_run(row)
            bug_dir = self.bug_dir(bug)
            if os.path.isdir(bug_dir):
                snapshot_ground_truth(self.soapfl_dir, bug_dir, self.python)
            if row["status"] in ("ok", "no_result", "interrupted") or row["error_class"] not in RETRYABLE:
                break
        return row or {"bug": bug.name, "status": "interrupted", "error_class": "interrupted", "wall_s": 0}

    # ------------------------------------------------------------------ batch
    def run(self, bugs: List[Bug]) -> dict:
        os.makedirs(self.out_dir, exist_ok=True)
        meta = build_meta(self.name, self.soapfl_dir, self.config, self.model, self.lenient, self.seed,
                          self.patches_dir, self.pipeline)
        check_or_write_meta(self.out_dir, meta, self.allow_meta_change)
        if self.pipeline == "hypodeduce":
            # the exact chain and prompts used, kept with the results (written once, before the workers start)
            from .hypodeduce.config import build_configs
            build_configs(self.soapfl_dir, os.path.join(self.out_dir, "_hypodeduce_config"))

        todo = [b for b in bugs if not self.is_finished(b)]
        skipped = len(bugs) - len(todo)
        self.progress(f"{len(bugs)} bugs selected, {skipped} already finished, {len(todo)} to run "
                      f"({self.jobs} parallel, timeout {self.timeout}s) -> {self.out_dir}")

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
        return {"selected": len(bugs), "skipped_finished": skipped, "ran": len(todo),
                "status_counts": counts, "out_dir": self.out_dir}
