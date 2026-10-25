import json
import os

from fl_tools import context as ctx
from fl_tools.bugs import Bug

TRACE = ["--- a.BTest::testParse", "java.lang.NumberFormatException: bad sign",
         "\tat a.B.parseValue(B.java:12)", "\tat a.B$Inner.<init>(B.java:40)", "\tat a.BTest.testParse(BTest.java:7)"]


class M:
    def __init__(self, covered=True, code="", src_id=None):
        self._covered, self.code, self.src_id, self.doc = covered, code, src_id, ""


class JC:
    def __init__(self, name):
        self.class_name, self.methods = name, {}


class TM:
    class_name, signature, code = "a.BTest", "testParse()", "void testParse() { B.parseValue(\"-1\"); // error occurred here }"


class FakeBackend:
    def __init__(self):
        self.calls = []

    def export(self, prop, buggy):
        return {"tests.trigger": "a.BTest::testParse\na.BTest::testOther", "dir.src.classes": "src",
                "dir.src.tests": "test", "classes.modified": "LEAK"}[prop]

    def checkout(self, bug, dest):
        os.makedirs(dest)
        self.calls.append(("checkout", dest))

    def test_facts(self, name, buggy, tmp, test_src):
        b = JC("a.B")
        b.methods = {"a.B::parseValue(String)": M(), "a.B::toString()": M(covered=False),
                     "a.B$Inner::Inner()": M()}
        other = JC("x.Unrelated")
        other.methods = {"x.Unrelated::f()": M()}
        return {"output": ["bad sign\n"], "trace": [l + "\n" for l in TRACE], "test_method": TM(), "helpers": [],
                "covered_classes": [b, other]}

    def methods_code(self, classes, src, buggy):
        for c in classes:
            for k, m in c.methods.items():
                m.src_id, m.code = k, f"/* code of {k} */"
        return classes


def test_parse_frames_and_keys():
    fr = ctx.parse_frames(TRACE)
    assert [f["key"] for f in fr] == ["a.B::parseValue", "a.B$Inner::Inner", "a.BTest::testParse"]
    assert fr[0]["line"] == 12 and ctx.method_key("a.B::parseValue(String)") == "a.B::parseValue"


def test_gather_bug_uses_only_buggy_side_and_summarizes(tmp_path):
    be = FakeBackend()
    out = ctx.gather_bug(Bug("Lang", 1), be, str(tmp_path / "work"), str(tmp_path / "results"), {"a.B"}, max_tests=1)
    assert out["failing_tests_total"] == 2 and len(out["tests"]) == 1
    m = out["methods"]
    assert m["a.B::parseValue(String)"] == {"failing_tests_covering": 1, "stack_depth": 0}
    assert m["a.B$Inner::Inner()"]["stack_depth"] == 1 and "a.B::toString()" not in m
    assert m["x.Unrelated::f()"]["stack_depth"] is None
    assert set(out["method_code"]) == {"a.B::parseValue(String)", "a.B$Inner::Inner()"}   # only wanted classes
    assert "LEAK" not in json.dumps(out) and "error occurred here" in out["tests"][0]["test_method"]["code"]
    assert be.calls and not os.path.exists(be.calls[0][1])          # temporary checkout removed


def test_reuses_checkout_left_in_results(tmp_path):
    buggy = tmp_path / "results" / "run1" / "d4j1.4.0-Lang-1" / "buggy"
    buggy.mkdir(parents=True)
    (buggy / ".defects4j.config").write_text("x")
    be = FakeBackend()
    out = ctx.gather_bug(Bug("Lang", 1), be, str(tmp_path / "w"), str(tmp_path / "results"), set())
    assert not be.calls and out["source"].startswith("checkout reused")
    assert len(out["tests"]) == 2


def test_candidate_classes_and_default_dir(tmp_path):
    d = tmp_path / "reports" / "run" / "bugs" / "d4j1.4.0-Lang-1"
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps({"buggy_methods": [{"method_name": "a.B::f()"}]}))
    assert ctx.candidate_classes_of([str(tmp_path / "reports" / "run")], "d4j1.4.0-Lang-1") == {"a.B"}
    assert ctx.bugs_of_run(str(tmp_path / "reports" / "run")) == ["d4j1.4.0-Lang-1"]
    assert ctx.default_context_dir(str(tmp_path / "reports" / "run")) is None
    (tmp_path / "reports" / "_failure_context").mkdir()
    assert ctx.default_context_dir(str(tmp_path / "reports" / "run")).endswith("_failure_context")
