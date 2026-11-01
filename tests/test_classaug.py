import json
import types

import pytest

from fl_tools import classaug
from fl_tools.bugs import parse_bugs

CTX = {"tests": [{"name": "a.ParserTest::testSign", "frames": []}],
       "methods": {"a.Lexer::next()": {"failing_tests_covering": 1, "stack_depth": None},
                   "a.Parser::parse(String)": {"failing_tests_covering": 1, "stack_depth": None},
                   "a.Util$Inner::fail()": {"failing_tests_covering": 1, "stack_depth": 0},
                   "a.Util::helper()": {"failing_tests_covering": 1, "stack_depth": 3},
                   "a.ParserTest::testSign()": {"failing_tests_covering": 1, "stack_depth": 1}}}


def test_rank_classes_stack_then_name_then_coverage():
    r = classaug.rank_classes(CTX)
    assert r[0] == "a.Util"                    # on the stack (depth 0, inner class -> outer class)
    assert r[1] == "a.Parser"                  # name overlap with the failing test class ParserTest
    assert "a.ParserTest" not in r and classaug.rank_classes(None) == []


def test_decide_always_and_gated():
    rank = ["a.Util", "a.Parser", "a.Lexer"]
    avail = {"a.Util": 1, "a.Parser": 1, "a.Lexer": 1}
    d = classaug.decide(["a.Parser"], rank, avail, "always", 3)
    assert d["added"] == ["a.Util", "a.Lexer"] and not d["agree"]
    assert classaug.decide(["a.Util"], rank, avail, "gated", 3)["added"] == []          # agrees: plain SoapFL
    assert classaug.decide(["a.Parser"], rank, avail, "gated", 2)["added"] == ["a.Util"]
    assert classaug.decide([], rank, {"a.Lexer": 1}, "always", 3)["added"] == ["a.Lexer"]  # only offered classes


def test_install_wraps_soapfl_class_phase(monkeypatch):
    class Env:
        def __init__(self):
            self.env_dict = {"classes_dict": {"a.Util": 1, "a.Parser": 1}}
            self.res_dict = {"buggy_classes": []}
            self.test_suite = types.SimpleNamespace(name="a.ParserTest")

    class SearchSuspiciousClass:
        def update_chat_env(self, chat_env):
            chat_env.env_dict["suspicious_classes"] = ["a.Parser"]
            chat_env.res_dict["buggy_classes"] = ["a.Parser"]
            return chat_env

    mod = types.SimpleNamespace(SearchSuspiciousClass=SearchSuspiciousClass)
    monkeypatch.setenv(classaug.ENV_RANKING, json.dumps(["a.Util", "a.Parser"]))
    monkeypatch.setenv(classaug.ENV_MODE, "gated")
    monkeypatch.setenv(classaug.ENV_K, "3")
    classaug.install(mod)
    env = SearchSuspiciousClass().update_chat_env(Env())
    assert env.env_dict["suspicious_classes"] == ["a.Parser", "a.Util"]
    assert env.res_dict["class_augment"][0]["added"] == ["a.Util"]


def test_runner_passes_ranking_and_entry(tmp_path, monkeypatch):
    from fl_tools.experiment import configure_classaug
    from fl_tools.runner import Runner
    for k in ("SOAPFL_CA_MODE", "SOAPFL_CA_K", "SOAPFL_CA_CONTEXT"):
        monkeypatch.setenv(k, "x")          # registers the original state, so the test does not leak settings
    ctxdir = tmp_path / "ctx"
    ctxdir.mkdir()
    (ctxdir / "d4j1.4.0-Lang-1.json").write_text(json.dumps(CTX))
    cfg = configure_classaug({"k": 2, "mode": "gated", "context": str(ctxdir)})
    assert cfg["mode"] == "gated"
    r = Runner(name="x", results_dir=str(tmp_path), soapfl_dir=str(tmp_path), pipeline="classaug")
    bug = parse_bugs("Lang-1")[0]
    assert r._command(bug)[1:3] == ["-m", "fl_tools.classaug"]
    env = r._env(bug)
    assert json.loads(env[classaug.ENV_RANKING])[0] == "a.Util" and env["SOAPFL_CA_MODE"] == "gated"
    assert json.loads(r._env(parse_bugs("Lang-2", include_deprecated=True)[0])[classaug.ENV_RANKING]) == []
    with pytest.raises(ValueError):
        configure_classaug({"context": str(tmp_path / "missing")})


def test_test_classes_never_ranked():
    ctx = {"tests": [{"name": "org.jfree.chart.plot.junit.PiePlot3DTests::testDraw", "frames": []}],
           "methods": {"org.jfree.chart.plot.junit.PiePlot3DTests::testDraw()": {"failing_tests_covering": 1, "stack_depth": 0},
                       "org.jfree.chart.plot.PiePlot3D::draw()": {"failing_tests_covering": 1, "stack_depth": 1},
                       "org.jfree.chart.plot.PiePlot::initialise()": {"failing_tests_covering": 1, "stack_depth": None},
                       "a.b.FooTestCase::setUp()": {"failing_tests_covering": 1, "stack_depth": None}}}
    assert classaug.rank_classes(ctx) == ["org.jfree.chart.plot.PiePlot3D", "org.jfree.chart.plot.PiePlot"]
