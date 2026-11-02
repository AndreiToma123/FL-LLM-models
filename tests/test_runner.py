import json
import os
import sys

import pytest

from fl_tools.bugs import parse_bugs
from fl_tools.runner import MetaMismatch, Runner, classify_failure

STUB = r'''
import argparse, json, os, sys, time
p = argparse.ArgumentParser()
for a in ("--config", "--version", "--project", "--bugID", "--output", "--model"):
    p.add_argument(a)
a = p.parse_args()
name = f"{a.project}-{a.bugID}"
d = os.path.join(a.output, f"d4j{a.version}-{name}")
os.makedirs(d, exist_ok=True)
assert os.environ["SOAPFL_RUN_DIR"] == d and os.environ["PYTHONHASHSEED"] == "0"
if a.bugID == "2":
    print("openai.APIConnectionError: Connection error."); sys.exit(1)
if a.bugID == "3":
    print("ValueError: Invalid Method Review Conclusion"); sys.exit(1)
if a.bugID == "4":
    time.sleep(30)
if int(a.bugID) >= 100:
    print("AssertionError: Error: No instrument file:"); sys.exit(1)
json.dump({"buggy_methods": [{"class_name": "A", "method_name": "A::f()", "score": 9}], "buggy_codes": {}},
          open(os.path.join(d, "result.json"), "w"))
json.dump({"buggy_methods": ["A::f()"]}, open(os.path.join(d, "ground_truth.json"), "w"))
'''


@pytest.fixture
def soapfl(tmp_path):
    d = tmp_path / "SoapFL"
    d.mkdir()
    (d / "run.py").write_text(STUB)
    return str(d)


def make(tmp_path, soapfl, **kw):
    args = dict(name="t", results_dir=str(tmp_path / "res"), soapfl_dir=soapfl, python=sys.executable,
                timeout=10, retries=1, progress=lambda m: None, patches_dir=str(tmp_path))
    args.update(kw)
    return Runner(**args)


def test_batch_resume_and_classification(tmp_path, soapfl):
    bugs = parse_bugs("Lang-1:3")
    r = make(tmp_path, soapfl)
    out = r.run(bugs)
    assert out["status_counts"] == {"ok": 1, "failed": 2}
    runs = [json.loads(l) for l in open(os.path.join(r.out_dir, "runs.jsonl"))]
    classes = {(x["bug"], x["error_class"]) for x in runs if x["status"] == "failed"}
    assert ("Lang-2", "server_unreachable") in classes      # retried once (transient)
    assert ("Lang-3", "score_parse") in classes
    assert sum(1 for x in runs if x["bug"] == "Lang-2") == 2
    assert sum(1 for x in runs if x["bug"] == "Lang-3") == 1  # not transient -> no retry
    out2 = make(tmp_path, soapfl).run(bugs)
    # Lang-3 failed for good -> skipped on resume; Lang-2 (server unreachable, transient) is tried again
    assert out2["skipped_finished"] == 1 and out2["skipped_failed"] == 1 and out2["ran"] == 1
    out3 = make(tmp_path, soapfl, retry_failed=True).run(bugs)
    assert out3["skipped_failed"] == 0 and out3["ran"] == 2


def test_tail_guard_stops_a_straggler(tmp_path, soapfl):
    """Once every bug has started, a bug running far longer than the finished ones is stopped
    (2026-11-02: one hung bug held the GPU for hours while the other 387 were done)."""
    bugs = parse_bugs("Lang-5:14") + parse_bugs("Lang-4")
    r = make(tmp_path, soapfl, timeout=60, retries=0, jobs=11, tail_factor=3, tail_min=2, heartbeat=0.3)
    out = r.run(bugs)
    rows = {x["bug"]: x for x in (json.loads(l) for l in open(os.path.join(r.out_dir, "runs.jsonl")))}
    assert rows["Lang-4"]["status"] == "timeout" and rows["Lang-4"]["error_class"] == "tail_timeout"
    assert rows["Lang-4"]["wall_s"] < 20
    assert out["status_counts"] == {"ok": 10, "timeout": 1}


def test_circuit_breaker(tmp_path, soapfl):
    """Most bugs failing = broken setup: stop instead of spending the budget."""
    r = make(tmp_path, soapfl, retries=0, jobs=2, breaker_min=6, breaker_rate=0.5)
    out = r.run(parse_bugs("Closure-100:130"))
    rows = [json.loads(l) for l in open(os.path.join(r.out_dir, "runs.jsonl"))]
    assert out["circuit_breaker"]
    assert len([x for x in rows if x["status"] == "failed"]) < 15


def test_timeout(tmp_path, soapfl):
    r = make(tmp_path, soapfl, timeout=1, retries=0)
    out = r.run(parse_bugs("Lang-4"))
    assert out["status_counts"] == {"timeout": 1}


def test_meta_guard(tmp_path, soapfl):
    make(tmp_path, soapfl).run(parse_bugs("Lang-1"))
    with pytest.raises(MetaMismatch):
        make(tmp_path, soapfl, lenient=False).run(parse_bugs("Lang-5"))
    make(tmp_path, soapfl, lenient=False, allow_meta_change=True).run(parse_bugs("Lang-5"))


def test_parallel(tmp_path, soapfl):
    out = make(tmp_path, soapfl, jobs=3).run(parse_bugs("Lang-5:10"))
    assert out["status_counts"] == {"ok": 6}


def test_classify_failure():
    assert classify_failure("This model's maximum context length is 8192 tokens") == "context_overflow_server"
    assert classify_failure("xx") == "other"


def test_sigterm_stops_without_retrying(tmp_path, soapfl):
    """Slurm's time-limit warning ends in SIGTERM: running bugs are killed, marked 'interrupted',
    not retried, and the CLI exits 130 quickly (CSC job script relies on this)."""
    import signal
    import subprocess
    import time
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.Popen([sys.executable, "-m", "fl_tools", "run", "--name", "t", "--bugs", "Lang-4",
                             "--results-dir", str(tmp_path / "res"), "--soapfl-dir", soapfl,
                             "--retries", "2", "--skip-preflight", "--timeout", "60"],
                            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    runs = tmp_path / "res" / "t" / "runs.jsonl"
    log_dir = tmp_path / "res" / "t" / "_logs"
    deadline = time.time() + 20
    while not (log_dir / "Lang-4.log").exists() and time.time() < deadline:
        time.sleep(0.2)
    time.sleep(1)
    started = time.time()
    proc.send_signal(signal.SIGTERM)
    out, _ = proc.communicate(timeout=20)
    assert proc.returncode == 130, out
    assert time.time() - started < 15
    rows = [json.loads(l) for l in open(runs)]
    assert [r["status"] for r in rows] == ["interrupted"], rows
