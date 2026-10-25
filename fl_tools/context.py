"""Failure-context export: what a developer sees when the tests fail, saved per bug for the selectors.

For each bug (model-independent, so one file serves every run): the failing tests (at most --max-tests), each
with its error output, stack trace, test method source (SoapFL marks the failing line with
"// error occurred here") and the test helper methods it ran; the production methods each failing test
executed (coverage, from SoapFL's class tracer); and the source of covered methods in the classes that
matter (classes on the stack trace and classes of the stored candidates), capped per bug.

NOT collected, to avoid leaking the answer: the fixed version, `classes.modified`, VCS history, bug
reports, SoapFL's `buggy_methods`. Only the buggy checkout is used.

Runs inside the Docker image / CSC container (needs Defects4J, Java and SoapFL's functions):
    python -m fl_tools context results/run100-qwen25coder --jobs 4
Output: results/_failure_context/<d4j dir>.json, copied to reports/_failure_context/ (small JSON files).
Resumable: bugs with a file are skipped. CPU only, no model calls.
"""
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Iterable, List, Optional, Set

from . import __version__
from .bugs import VERSION, Bug, bug_from_dirname

CONTEXT_DIRNAME = "_failure_context"
FORMAT = 1
MAX_TESTS = 3                 # failing tests per bug (SoapFL also samples); the total is recorded
MAX_OUTPUT_CHARS = 4000
MAX_METHODS_WITH_CODE = 400
MAX_CODE_CHARS_TOTAL = 1_200_000
FRAME_RE = re.compile(r"^\s*at ([\w$.]+)\.([\w$<>]+)\(([^)]*)\)")


# --------------------------------------------------------------------------- pure helpers (tested offline)
def parse_frames(stack_trace: List[str]) -> List[dict]:
    """'\\tat a.b.C$D.m(C.java:12)' -> {'class': 'a.b.C$D', 'method': 'm', 'line': 12, 'key': 'a.b.C$D::m'}."""
    frames = []
    for line in stack_trace:
        m = FRAME_RE.match(line)
        if not m:
            continue
        cls, meth, where = m.groups()
        if meth == "<init>":
            meth = cls.split(".")[-1].split("$")[-1]
        ln = re.search(r":(\d+)", where)
        frames.append({"class": cls, "method": meth, "line": int(ln.group(1)) if ln else None,
                       "key": f"{cls}::{meth}"})
    return frames


def method_key(method_name: str) -> str:
    """'a.b.C$D::m(int,String)' -> 'a.b.C$D::m' (frames carry no parameter types)."""
    return method_name.split("(")[0]


def method_class(method_name: str) -> str:
    return method_name.split("::")[0]


def outer_class(cls: str) -> str:
    return cls.split("$")[0]


def summarize(tests: List[dict], code: Dict[str, dict], n_failing_total: int, bug: str,
              source_note: str) -> dict:
    """Assemble the per-bug file from per-test facts. Per covered method: how many failing tests ran it and
    the smallest stack depth at which its name appears (0 = top frame; overloads share a name)."""
    methods: Dict[str, dict] = {}
    for t_index, t in enumerate(tests):
        depth_of = {}
        for depth, fr in enumerate(t.get("frames") or []):
            depth_of.setdefault(fr["key"], depth)
        for m in t.get("covered_methods") or []:
            e = methods.setdefault(m, {"failing_tests_covering": 0, "stack_depth": None})
            e["failing_tests_covering"] += 1
            d = depth_of.get(method_key(m))
            if d is not None and (e["stack_depth"] is None or d < e["stack_depth"]):
                e["stack_depth"] = d
    return {"format": FORMAT, "bug": bug, "version": VERSION, "tool": f"fl_tools {__version__}",
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": source_note,
            "failing_tests_total": n_failing_total, "tests": tests, "methods": methods, "method_code": code}


def load_context(context_dir: Optional[str], bug_dirname: str) -> Optional[dict]:
    if not context_dir:
        return None
    path = os.path.join(context_dir, bug_dirname + ".json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_context_dir(run_dir: str) -> Optional[str]:
    """reports/<run>/ -> reports/_failure_context ; results/<run>/ -> results/_failure_context."""
    d = os.path.join(os.path.dirname(os.path.normpath(run_dir)), CONTEXT_DIRNAME)
    return d if os.path.isdir(d) else None


# --------------------------------------------------------------------------- Defects4J + SoapFL backend
class SoapFLBackend:
    """Runs the failing tests with SoapFL's own helpers (instrumentation agent, tree-sitter extractor)."""

    def __init__(self, soapfl_dir: str):
        self.soapfl_dir = soapfl_dir
        if soapfl_dir not in sys.path:
            sys.path.insert(0, soapfl_dir)
        from functions import d4j, instrument, line_parser   # noqa: F401  (SoapFL, Apache-2.0)
        from functions.utils import run_cmd
        self.d4j, self.instrument, self.lp, self.run_cmd = d4j, instrument, line_parser, run_cmd

    def export(self, prop: str, buggy: str) -> str:
        out, _ = self.run_cmd(f"defects4j export -p {prop} -w {buggy}")
        return out.strip()

    def checkout(self, bug: Bug, dest: str) -> None:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        self.run_cmd(f"defects4j checkout -p {bug.project} -v {bug.id}b -w {dest}")
        if not os.path.isdir(dest):
            raise RuntimeError(f"checkout failed for {bug}")

    def test_facts(self, test_name: str, buggy: str, tmp: str, test_src: str) -> dict:
        os.makedirs(tmp, exist_ok=True)
        output, trace = self.d4j.run_single_test(test_name, buggy, tmp)
        self.instrument.run_instrument(test_name, buggy, tmp, self.d4j.agent_jar, mode="test")
        with open(os.path.join(tmp, "run_test.log"), "r") as f:
            ran = f.readlines()
        test_method, helpers = None, []
        try:
            test_method, helpers = self.d4j.get_test_code(buggy, test_src, ran, trace)
        except Exception as exc:          # SoapFL's helper fails on some unusual test layouts
            helpers = []
            test_method = None
            print(f"warning: test code of {test_name} not extracted: {exc}", file=sys.stderr)
        self.instrument.run_instrument(test_name, buggy, tmp, self.d4j.agent_jar, mode="src")
        _, covered = self.lp.parse_coverage(os.path.join(tmp, "inst_src.log"), os.path.join(tmp, "run_src.log"))
        return {"output": output, "trace": trace, "test_method": test_method, "helpers": helpers,
                "covered_classes": covered}

    def methods_code(self, classes, src_path: str, buggy: str):
        """JavaClass objects with source code filled in (SoapFL's get_classes_code)."""
        return self.d4j.get_classes_code(classes, src_path, buggy)


def _obj_method(m) -> Optional[dict]:
    if m is None:
        return None
    return {"class": getattr(m, "class_name", ""), "signature": getattr(m, "signature", ""),
            "code": getattr(m, "code", "") or ""}


def gather_bug(bug: Bug, backend, work_root: str, results_root: str, candidate_classes: Set[str],
               max_tests: int = MAX_TESTS) -> dict:
    """Collect one bug's context. Reuses a buggy checkout a previous run left in results/, else checks out."""
    buggy, temp_checkout = None, None
    for run in sorted(os.listdir(results_root)) if os.path.isdir(results_root) else []:
        cand = os.path.join(results_root, run, bug.dirname, "buggy")
        if any(os.path.isfile(os.path.join(cand, f)) for f in (".defects4j.config", "defects4j.build.properties")):
            buggy = cand
            break
    if buggy is None:
        temp_checkout = os.path.join(work_root, "_checkouts", bug.dirname, "buggy")
        if os.path.isdir(temp_checkout):
            shutil.rmtree(os.path.dirname(temp_checkout))
        backend.checkout(bug, temp_checkout)
        buggy = temp_checkout
    try:
        triggers = [t for t in backend.export("tests.trigger", buggy).split("\n") if t.strip()]
        src_path = backend.export("dir.src.classes", buggy)
        test_src = backend.export("dir.src.tests", buggy)
        tests, covered_by_class = [], {}
        for name in sorted(triggers)[:max_tests]:
            tmp = os.path.join(work_root, "_tmp", bug.dirname, name.replace("::", "__"))
            facts = backend.test_facts(name, buggy, tmp, test_src)
            covered_ids = []
            for jc in facts["covered_classes"]:
                keep = {k: m for k, m in jc.methods.items() if getattr(m, "_covered", False)}
                if not keep:
                    continue
                merged = covered_by_class.setdefault(jc.class_name, jc.__class__(jc.class_name))
                merged.methods.update(keep)
                covered_ids += list(keep)
            output = "".join(facts["output"] or [])
            trace = [l.rstrip("\n") for l in (facts["trace"] or [])]
            tests.append({"name": name, "output": output[:MAX_OUTPUT_CHARS], "stack_trace": trace,
                          "frames": parse_frames(trace), "test_method": _obj_method(facts["test_method"]),
                          "helper_methods": [_obj_method(h) for h in facts["helpers"] or []][:10],
                          "covered_methods_inst": covered_ids})
        # source ids and code for covered methods of the classes that matter
        frame_classes = {outer_class(fr["class"]) for t in tests for fr in t["frames"]}
        wanted = {outer_class(c) for c in candidate_classes} | frame_classes
        classes = [c for name, c in covered_by_class.items() if name in wanted]
        try:
            classes = backend.methods_code(classes, src_path, buggy) if classes else []
        except Exception as exc:          # e.g. SoapFL's assertion when a method's source is not found
            print(f"warning: method code for {bug} not extracted: {exc}", file=sys.stderr)
            classes = []
        inst_to_src, code, total = {}, {}, 0
        for jc in classes:
            for inst_id, m in jc.methods.items():
                src_id = getattr(m, "src_id", None) or inst_id
                inst_to_src[inst_id] = src_id
                body = getattr(m, "code", "") or ""
                if len(code) < MAX_METHODS_WITH_CODE and total + len(body) <= MAX_CODE_CHARS_TOTAL:
                    code[src_id] = {"code": body, "doc": getattr(m, "doc", "") or ""}
                    total += len(body)
        for t in tests:
            t["covered_methods"] = sorted({inst_to_src.get(i, i) for i in t.pop("covered_methods_inst")})
        note = "checkout reused from results/" if temp_checkout is None else "fresh buggy checkout"
        return summarize(tests, code, len(triggers), bug.name, note)
    finally:
        if temp_checkout and os.path.isdir(os.path.dirname(temp_checkout)):
            shutil.rmtree(os.path.dirname(temp_checkout), ignore_errors=True)


# --------------------------------------------------------------------------- driver
def candidate_classes_of(run_dirs: Iterable[str], bug_dirname: str) -> Set[str]:
    out: Set[str] = set()
    for run in run_dirs:
        for path in (os.path.join(run, bug_dirname, "result.json"), os.path.join(run, "bugs", bug_dirname, "result.json")):
            if os.path.exists(path):
                try:
                    res = json.load(open(path, encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                out |= {method_class(m.get("method_name", "")) for m in res.get("buggy_methods") or []}
    return {c for c in out if c}


def bugs_of_run(run_dir: str) -> List[str]:
    names = set()
    for base in (run_dir, os.path.join(run_dir, "bugs")):
        if os.path.isdir(base):
            names |= {d for d in os.listdir(base) if d.startswith("d4j") and os.path.isdir(os.path.join(base, d))}
    return sorted(names)


def _one(args) -> dict:
    import warnings
    # SoapFL's tree-sitter version prints a harmless FutureWarning in every worker; keep the progress readable
    warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")
    bug_dirname, soapfl_dir, work_root, results_root, classes, out_dir, copy_dir, max_tests = args
    started = time.time()
    try:
        ctx = gather_bug(bug_from_dirname(bug_dirname), SoapFLBackend(soapfl_dir), work_root, results_root,
                         set(classes), max_tests)
        ctx["seconds"] = round(time.time() - started, 1)
        path = os.path.join(out_dir, bug_dirname + ".json")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(ctx, f, indent=1)
        os.replace(path + ".tmp", path)
        if copy_dir:
            os.makedirs(copy_dir, exist_ok=True)
            shutil.copy2(path, os.path.join(copy_dir, bug_dirname + ".json"))
        return {"bug": bug_dirname, "ok": True, "tests": len(ctx["tests"]), "methods": len(ctx["methods"]),
                "with_code": len(ctx["method_code"]), "seconds": ctx["seconds"]}
    except Exception as exc:
        return {"bug": bug_dirname, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "seconds": round(time.time() - started, 1)}


def export_contexts(run_dirs: List[str], soapfl_dir: str, results_root: str, reports_root: Optional[str],
                    jobs: int = 2, max_tests: int = MAX_TESTS, only: Optional[Set[str]] = None,
                    progress=print) -> List[dict]:
    out_dir = os.path.join(results_root, CONTEXT_DIRNAME)
    copy_dir = os.path.join(reports_root, CONTEXT_DIRNAME) if reports_root else None
    os.makedirs(out_dir, exist_ok=True)
    bugs = sorted({b for r in run_dirs for b in bugs_of_run(r)})
    if only:
        bugs = [b for b in bugs if b.split("-", 1)[1] in only]
    todo = []
    for b in bugs:
        done = os.path.join(out_dir, b + ".json")
        if os.path.exists(done):
            if copy_dir and not os.path.exists(os.path.join(copy_dir, b + ".json")):
                os.makedirs(copy_dir, exist_ok=True)
                shutil.copy2(done, os.path.join(copy_dir, b + ".json"))
            continue
        todo.append((b, soapfl_dir, out_dir, results_root, sorted(candidate_classes_of(run_dirs, b)),
                     out_dir, copy_dir, max_tests))
    progress(f"failure context: {len(bugs)} bugs, {len(bugs) - len(todo)} already done, {len(todo)} to collect "
             f"({jobs} in parallel)")
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(_one, t) for t in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            rows.append(r)
            progress(f"  [{i}/{len(todo)}] {r['bug']}: " + (
                f"{r['tests']} tests, {r['methods']} covered methods, code for {r['with_code']}, {r['seconds']} s"
                if r["ok"] else f"FAILED {r['error']}"))
    with open(os.path.join(out_dir, "_log.jsonl"), "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows
