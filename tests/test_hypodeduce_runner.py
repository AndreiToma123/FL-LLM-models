"""The full path a real run takes: Runner(pipeline="hypodeduce") -> fl_tools.hypodeduce.soapfl_entry ->
SoapFL's run.main() with our chain -> result.json -> ground truth -> score / funnel / ties.

Only Defects4J is faked, through a sitecustomize.py that the SoapFL subprocess picks up from PYTHONPATH
(checkout is a no-op, the failing test and the covered classes are invented). Needs SOAPFL_DIR.
"""
import json
import os
import shutil
import sys

import pytest

from fl_tools.bugs import parse_bugs
from fl_tools.funnel import analyse_run
from fl_tools.mock_server import start_mock_server
from fl_tools.runner import Runner
from fl_tools.score import score_run
from fl_tools.ties import analyse_run as analyse_ties

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOAPFL = os.environ.get("SOAPFL_DIR", os.path.join(ROOT, "external", "SoapFL"))
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(SOAPFL, "camel", "local_llm.py")),
                                reason="patched SoapFL checkout not found (set SOAPFL_DIR)")

SITECUSTOMIZE = r'''
import os, sys
if os.environ.get("HD_FAKE_D4J") and os.path.exists("run.py"):
    from types import SimpleNamespace as NS
    sys.path.insert(0, os.getcwd())
    import run
    from chatdev.test_suite import TestCase, TestFailure, TestMethod, TestSuite
    tm = TestMethod(name="testIt", class_name="pkg.FooTest", signature="testIt()", code="void testIt() {}", comment="")
    case = TestCase(name="pkg.FooTest::testIt", test_method=tm, test_utility_methods=[],
                    test_output=["expected 2 but was 3"], stack_trace=["at pkg.Baz.qux(Baz.java:3)"])
    run.check_out = lambda *a, **k: None
    def fake_failed_tests(version, project, bug_id, project_path, cache_path):
        os.makedirs(cache_path, exist_ok=True)      # the real one creates the cache folder too
        return TestFailure(project="Lang", bug_ID=1, test_suites=[TestSuite(name="pkg.FooTest", test_cases=[case])],
                           buggy_methods=["pkg.Baz::qux(int)"])
    run.get_failed_tests = fake_failed_tests
    import fl_tools.hypodeduce.phases as phases
    m = lambda src, code: NS(src_id=src, doc="", code=code, enhanced_doc="")
    classes = {"pkg.Foo": NS(class_name="pkg.Foo", doc="", methods={"bar": m("pkg.Foo::bar()", "int bar() {}")}),
               "pkg.Baz": NS(class_name="pkg.Baz", doc="", methods={"qux": m("pkg.Baz::qux(int)", "int qux(int i) {}")})}
    phases.covered_classes_prompt = lambda *a, **k: ("pkg.Foo\npkg.Baz\n\n", classes)
'''

RULES = [
    {"match": r"explain the code logic", "reply": "1) testIt calls qux."},
    {"match": r"DIFFERENT hypotheses", "reply": "Hypothesis 1: null in Foo.bar\nHypothesis 2: off-by-one in Baz.qux"},
    {"match": r"Hypothesis: \s*\"null in Foo", "reply": "1. #pkg.Foo#"},
    {"match": r"Hypothesis: \s*\"off-by-one", "reply": "1. #pkg.Baz#"},
    {"match": r"Method Summary", "reply": "| Method Full Name | Method Summary |\n| --- | --- |"},
    {"match": r"(?s)class pkg\.Foo may be problematic", "reply": "[1] **pkg.Foo::bar()**: x"},
    {"match": r"(?s)class pkg\.Baz may be problematic", "reply": "[1] **pkg.Baz::qux(int)**: x"},
    {"match": r"(?s)Possible Causes: \s*\"null in Foo.*Full Name: \"pkg\.Foo::bar\(\)\"", "reply": "#8# maybe"},
    {"match": r"(?s)Possible Causes: \s*\"off-by-one.*Full Name: \"pkg\.Baz::qux\(int\)\"", "reply": "#8# likely"},
]


def test_runner_runs_hypodeduce_through_soapfl(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(SITECUSTOMIZE)
    srv = start_mock_server(rules=RULES, reply="no rule matched", max_model_len=16384)
    cache = os.path.join(SOAPFL, "cache", "d4j1.4.0-Lang-1")
    shutil.rmtree(cache, ignore_errors=True)
    try:
        for k, v in dict(SOAPFL_BASE_URL=srv.url, SOAPFL_API_KEY="x", SOAPFL_MODEL_NAME="mock-model",
                         SOAPFL_CONTEXT_LIMIT="16384", HD_FAKE_D4J="1", PYTHONPATH=str(site),
                         SOAPFL_HD_HYPOTHESES="2", SOAPFL_HD_CLASSES="1").items():
            monkeypatch.setenv(k, v)
        runner = Runner(name="hd", results_dir=str(tmp_path / "res"), soapfl_dir=SOAPFL, python=sys.executable,
                        pipeline="hypodeduce", config="HypoDeduce", timeout=120, retries=0,
                        progress=lambda m: None)
        out = runner.run(parse_bugs("Lang-1"))
        log = open(tmp_path / "res" / "hd" / "_logs" / "Lang-1.log").read()
        assert out["status_counts"] == {"ok": 1}, log[-3000:]
        run_dir = out["out_dir"]
        meta = json.load(open(os.path.join(run_dir, "run_meta.json")))
        assert meta["pipeline"] == "hypodeduce" and meta["llm_env"]["SOAPFL_HD_HYPOTHESES"] == "2"
        assert os.path.exists(os.path.join(run_dir, "_hypodeduce_config", "HypoDeduce", "PhaseConfig.json"))
        result = json.load(open(os.path.join(run_dir, "d4j1.4.0-Lang-1", "result.json")))
        # both hypotheses score 8 -> tie between hypotheses goes to hypothesis 1 (the model's first)
        assert result["hypodeduce"][0]["selected"] == 1
        assert [m["method_name"] for m in result["buggy_methods"]] == ["pkg.Foo::bar()", "pkg.Baz::qux(int)"]
        scored = score_run(run_dir, SOAPFL, write=False)
        assert "| ALL | 1 | 1 | 0 (0%) | 1 (100%) | 1 (100%) |" in scored["markdown"]
        funnel = analyse_run(run_dir, SOAPFL, write=False)
        assert "rank_2_5 | 1" in funnel["markdown"]
        ties = analyse_ties(run_dir, draws=50, write=False)["summary"]
        assert ties["buggy_method_in_ranking"] == 1 and ties["buggy_in_tie_group"] == 0   # (1,8) vs (0,8): no tie
    finally:
        srv.stop()
        shutil.rmtree(cache, ignore_errors=True)
