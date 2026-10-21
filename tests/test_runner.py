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
    assert out2["skipped_finished"] == 1 and out2["ran"] == 2


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
