import json
import os

from fl_tools.funnel import analyse_run, classify
from fl_tools.results import load_records
from fl_tools.score import rank_bug, score_run


def _bug(run, name, result=None, truth=None, events=(), status="ok"):
    d = run / f"d4j1.4.0-{name}"
    d.mkdir(parents=True)
    if result is not None:
        (d / "result.json").write_text(json.dumps(result))
    if truth is not None:
        (d / "ground_truth.json").write_text(json.dumps({"buggy_methods": truth}))
    with open(d / "events.jsonl", "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    with open(run / "runs.jsonl", "a") as f:
        f.write(json.dumps({"bug": name, "status": status, "wall_s": 5}) + "\n")


def _res(*methods):
    return {"buggy_methods": [{"class_name": m.split("::")[0], "method_name": m, "score": s}
                              for m, s in methods], "buggy_codes": {m: "" for m, _ in methods}}


def test_rank_bug():
    r = rank_bug(_res(("a.A::f()", 9), ("a.A::g()", 8)), ["a.A::g()"])
    assert r["method_rank"] == 2 and r["true_class"] == 1 and r["true_method"] == 0
    assert r["recall_ratio"] == "1|1" and r["false_positive"] == 1


def test_end_to_end(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    _bug(run, "Lang-1", _res(("a.A::f()", 9), ("a.A::g()", 9)), ["a.A::f()"],
         [{"type": "llm_call", "prompt_tokens": 100, "completion_tokens": 10}])
    _bug(run, "Lang-3", _res(("a.A::f()", 9), ("a.A::g()", 8)), ["a.A::g()"])
    _bug(run, "Math-1", _res(("b.B::x()", 9)), ["c.C::y()"])            # class missed
    _bug(run, "Math-2", None, ["c.C::y()"], [{"type": "no_valid_class"}], status="no_result")
    _bug(run, "Math-3", None, None, [], status="failed")
    out = score_run(str(run), write=True)
    s = out["summary"]["ALL"]
    assert (s["attempted"], s["top1"], s["top3"], s["top5"]) == (5, 1, 2, 2)
    assert os.path.exists(run / "per_bug_soapfl_format.csv")
    header = (run / "per_bug_soapfl_format.csv").read_text().splitlines()[0]
    assert header.count(",") == 9

    f = analyse_run(str(run))
    stages = {i["bug"]: i["stage"] for i in f["infos"]}
    assert stages == {"Lang-1": "top1", "Lang-3": "rank_2_5", "Math-1": "class_missed",
                      "Math-2": "no_valid_class", "Math-3": "crashed"}
    assert [i for i in f["infos"] if i["bug"] == "Lang-1"][0]["tie_group"] == 2
    assert "Tie-dependence: 1 of 1" in f["markdown"]


def test_not_run():
    from fl_tools.bugs import Bug
    from fl_tools.results import BugRecord
    assert classify(BugRecord(bug=Bug("Lang", 1), dir=None))["stage"] == "not_run"


def test_export(tmp_path):
    from fl_tools.export import export_run
    run = tmp_path / "run"
    run.mkdir()
    _bug(run, "Lang-1", _res(("a.A::f()", 9)), ["a.A::f()"])
    (run / "d4j1.4.0-Lang-1" / "huge.bin").write_bytes(b"x" * 10)
    (run / "summary.md").write_text("x")
    copied = export_run(str(run), str(tmp_path / "out"))
    assert "bugs/d4j1.4.0-Lang-1/result.json" in copied and "summary.md" in copied
    assert not (tmp_path / "out" / "bugs" / "d4j1.4.0-Lang-1" / "huge.bin").exists()
