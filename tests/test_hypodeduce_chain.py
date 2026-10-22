"""End-to-end test of the HypoDeduce chain inside the real (patched) SoapFL code, against the mock server.

Only Defects4J is faked (the covered classes of one invented bug); every phase, prompt fill-in, checkpoint,
parsing step, the selection and result.json come from the real code. Needs SOAPFL_DIR (skipped otherwise).
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

from fl_tools.mock_server import start_mock_server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOAPFL = os.environ.get("SOAPFL_DIR", os.path.join(ROOT, "external", "SoapFL"))
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(SOAPFL, "camel", "local_llm.py")),
                                reason="patched SoapFL checkout not found (set SOAPFL_DIR)")

DRIVER = r'''
import json, os, sys
from types import SimpleNamespace as NS
soapfl, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, soapfl)
os.chdir(soapfl)
import chatdev.phase as phase_module
from fl_tools.hypodeduce import phases
for name in phases.PHASES:
    setattr(phase_module, name, getattr(phases, name))
from fl_tools.hypodeduce.config import build_configs
from camel.typing import ModelType
from chatdev.chat_chain import ChatChain
from chatdev.test_suite import TestCase, TestMethod, TestSuite

def method(src, code):
    return NS(src_id=src, doc="", code=code, enhanced_doc="")
classes = {
    "pkg.Foo": NS(class_name="pkg.Foo", doc="Foo doc", methods={"bar": method("pkg.Foo::bar()", "int bar() { return x.y; }")}),
    "pkg.Baz": NS(class_name="pkg.Baz", doc="Baz doc", methods={"qux": method("pkg.Baz::qux(int)", "int qux(int i) { return i + 1; }")}),
    "pkg.Empty": NS(class_name="pkg.Empty", doc="", methods={}),
}
phases.covered_classes_prompt = lambda *a, **k: ("pkg.Foo\npkg.Baz\npkg.Empty\n\n\n", classes)

paths = build_configs(soapfl, os.path.join(out, "cfg"))
chain = ChatChain(config_path=paths[0], config_phase_path=paths[1], config_role_path=paths[2],
                  d4j_version="1.4.0", project_name="Demo", bug_ID=1, model_type=ModelType.LOCAL,
                  project_path=out, cache_dir=os.path.join(out, "cache"))
tm = TestMethod(name="testIt", class_name="pkg.FooTest", signature="testIt()", code="void testIt() {}", comment="")
case = TestCase(name="pkg.FooTest::testIt", test_method=tm, test_utility_methods=[],
                test_output=["expected 2 but was 3"], stack_trace=["at pkg.Baz.qux(Baz.java:3)"])
chain.test_suite = TestSuite(name="pkg.FooTest", test_cases=[case])
chain.test_cases = [case]
chain.pre_processing()
chain.make_recruitment()
chain.execute_chain()
chain.chat_env.write_result()
'''

RULES = [
    {"match": r"explain the code logic", "reply": "1) testIt calls qux and checks the result."},
    {"match": r"propose 3 DIFFERENT hypotheses",
     "reply": "Hypothesis 1: a null field is dereferenced in Foo.bar\n\nHypothesis 2: off-by-one error in Baz.qux\n"
              "Hypothesis 3: a constant is wrong somewhere"},
    # class search, one rule per hypothesis (C = 2)
    {"match": r"Hypothesis: \s*\"a null field", "reply": "1. #pkg.Foo#: null\n2. #pkg.Baz#: maybe"},
    {"match": r"Hypothesis: \s*\"off-by-one", "reply": "1. #pkg.Baz#: arithmetic\n2. #pkg.Empty#: also"},
    {"match": r"Hypothesis: \s*\"a constant", "reply": "1. #pkg.Nowhere#: not a covered class"},
    {"match": r"Method Summary", "reply": "| Method Full Name | Method Summary |\n| --- | --- |\n| pkg.Foo::bar() | reads y |"},
    # related methods per (hypothesis, class)
    {"match": r"(?s)class pkg\.Foo may be problematic.*Possible Causes: \s*\"a null field",
     "reply": "[1] **pkg.Foo::bar()**: dereferences x"},
    {"match": r"(?s)class pkg\.Baz may be problematic.*Possible Causes: \s*\"a null field",
     "reply": "[1] **pkg.Other::zzz()**: not in this class"},
    {"match": r"(?s)class pkg\.Baz may be problematic.*Possible Causes: \s*\"off-by-one",
     "reply": "[1] **pkg.Baz::qux(int)**: adds one"},
    # scores per (method, hypothesis)
    {"match": r"(?s)Possible Causes: \s*\"a null field.*Full Name: \"pkg\.Foo::bar\(\)\"", "reply": "#6# plausible"},
    {"match": r"(?s)Possible Causes: \s*\"off-by-one.*Full Name: \"pkg\.Baz::qux\(int\)\"", "reply": "#9# the + 1 is wrong"},
]


def run_chain(srv, env_extra, out=None):
    out = out or tempfile.mkdtemp()
    env = os.environ.copy()
    env.update(SOAPFL_BASE_URL=srv.url, SOAPFL_API_KEY="x", SOAPFL_MODEL_NAME="mock-model",
               SOAPFL_CONTEXT_LIMIT="16384", SOAPFL_RUN_DIR=out, SOAPFL_LENIENT_PARSING="1",
               PYTHONPATH=ROOT, PYTHONHASHSEED="0", PYTHONWARNINGS="ignore")
    env.update(env_extra)
    proc = subprocess.run([sys.executable, "-c", DRIVER, SOAPFL, out], capture_output=True, text=True, env=env,
                          timeout=120)
    return proc, out


def test_hypodeduce_chain_end_to_end():
    srv = start_mock_server(rules=RULES, reply="no rule matched", max_model_len=16384)
    try:
        proc, out = run_chain(srv, {"SOAPFL_HD_HYPOTHESES": "3", "SOAPFL_HD_CLASSES": "2"})
        assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
        result = json.load(open(os.path.join(out, "result.json")))
        ranked = [(m["method_name"], m["rank_key"], m["hypothesis"]) for m in result["buggy_methods"]]
        # hypothesis 2 is selected (best score 9); its method first, the other hypothesis's method after it
        assert ranked == [("pkg.Baz::qux(int)", [1, 9.0], 2), ("pkg.Foo::bar()", [0, 6.0], 1)]
        hd = result["hypodeduce"][0]
        assert hd["selected"] == 2 and len(hd["hypotheses"]) == 3
        assert hd["classes"] == {"1": ["pkg.Foo", "pkg.Baz"], "2": ["pkg.Baz", "pkg.Empty"], "3": []}
        assert hd["methods"]["1"] == {"pkg.Foo": ["pkg.Foo::bar()"], "pkg.Baz": []}
        assert result["buggy_classes"] == ["pkg.Foo", "pkg.Baz", "pkg.Empty"]   # retained by at least one hypothesis
        events = [json.loads(l) for l in open(os.path.join(out, "events.jsonl"))]
        kinds = [e["type"] for e in events]
        assert kinds.count("no_valid_class") == 1 and kinds.count("no_valid_method") == 1
        assert {"hd_hypotheses", "hd_classes", "hd_methods", "hd_selection"} <= set(kinds)
        # behaviour 1 + hypotheses 1 + classes 3 (one per hypothesis) + method docs 2 (Foo, Baz; once per
        # retained class, Empty has no methods) + related methods 3 (H1: Foo, Baz; H2: Baz) + reviews 2 (bar|H1, qux|H2)
        assert kinds.count("llm_call") == 12, kinds
        # a second run resumes from SoapFL's checkpoints: same result, no new model calls
        before = len(srv.requests)
        os.remove(os.path.join(out, "result.json"))
        proc2, _ = run_chain(srv, {"SOAPFL_HD_HYPOTHESES": "3", "SOAPFL_HD_CLASSES": "2"}, out=out)
        assert proc2.returncode == 0, proc2.stderr[-2000:]
        assert len(srv.requests) == before
        again = json.load(open(os.path.join(out, "result.json")))
        assert [m["method_name"] for m in again["buggy_methods"]] == [r[0] for r in ranked]
    finally:
        srv.stop()


def test_h1_c1_behaves_like_single_hypothesis():
    rules = [r for r in RULES if "propose 3" not in r["match"]]
    rules.insert(1, {"match": r"propose 1 DIFFERENT hypotheses", "reply": "Hypothesis 1: off-by-one error in Baz.qux"})
    srv = start_mock_server(rules=rules, reply="no rule matched", max_model_len=16384)
    try:
        proc, out = run_chain(srv, {"SOAPFL_HD_HYPOTHESES": "1", "SOAPFL_HD_CLASSES": "1"})
        assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
        result = json.load(open(os.path.join(out, "result.json")))
        assert [m["method_name"] for m in result["buggy_methods"]] == ["pkg.Baz::qux(int)"]
        assert result["hypodeduce"][0]["classes"] == {"1": ["pkg.Baz"]}
    finally:
        srv.stop()
