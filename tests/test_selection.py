import json
import os

from fl_tools.score import score_run
from fl_tools.selection import features, metrics, selectors
from fl_tools.selection.candidates import load_cases
from fl_tools.selection.replay import replay
from fl_tools.selection.split import make_split


def _m(name, score, causes="", code="", doc=""):
    return {"method_name": name, "class_name": name.split("::")[0], "score": score,
            "test_failure_causes": causes, "method_code": code, "method_doc": doc}


def _run(tmp_path, bugs):
    """bugs: {bug: (truth list, candidate list or None for a crash)}"""
    root = tmp_path / "run"
    runs = []
    for bug, (truth, cands) in bugs.items():
        d = root / "bugs" / f"d4j1.4.0-{bug}"
        d.mkdir(parents=True)
        (d / "ground_truth.json").write_text(json.dumps({"buggy_methods": truth}))
        if cands is not None:
            (d / "result.json").write_text(json.dumps({"buggy_methods": cands, "buggy_codes": {}}))
            runs.append({"bug": bug, "status": "ok"})
        else:
            runs.append({"bug": bug, "status": "failed", "error_class": "other"})
    (root / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in runs))
    return str(root)


CAUSES = "The failure comes from a.B::parseValue( which returns a wrong number when the input has a sign."


def test_metrics_mrr_map_and_oracle():
    from fl_tools.selection.candidates import BugCase
    c1 = BugCase("Lang-1", "Lang", "top1", {"x"}, [_m("x", 8), _m("y", 8)])
    c2 = BugCase("Lang-2", "Lang", "rank_2_5", {"x"}, [_m("y", 8), _m("x", 8), _m("z", 5)])
    c3 = BugCase("Lang-3", "Lang", "crashed", {"x"}, [])
    orders = {c.bug: c.candidates for c in (c1, c2, c3)}
    m = metrics.evaluate([c1, c2, c3], orders)
    assert (m["top1"], m["top3"], m["n"]) == (1, 2, 3) and abs(m["mrr"] - 0.5) < 1e-9
    assert metrics.average_precision([_m("a", 1), _m("x", 1)], {"x", "q"}) == 0.25
    assert metrics.oracle([c1, c2, c3])["top1"] == 2
    rnd = metrics.random_ties([c1, c2, c3], draws=400, seed=1)
    assert 0.8 < rnd["top1"]["mean"] < 1.2          # each tied pair: half the time first


def test_s0r_only_permutes_inside_ties():
    from fl_tools.selection.candidates import BugCase
    cands = [_m("a", 9), _m("b", 8), _m("c", 8), _m("d", 8), _m("e", 2)]
    case = BugCase("Math-1", "Math", "x", {"c"}, cands)
    for seed in range(5):
        order, _ = selectors.get("S0r").order(case, seed)
        names = [m["method_name"] for m in order]
        assert names[0] == "a" and names[-1] == "e" and set(names[1:4]) == {"b", "c", "d"}
    assert selectors.get("S0r").order(case, 3)[0] == selectors.get("S0r").order(case, 3)[0]   # deterministic


def test_lexical_features_and_s1():
    c_hit = _m("a.B::parseValue(String)", 8, CAUSES, code="int parseValue(String s) { return sign * n; }")
    c_miss = _m("a.B::toString()", 8, CAUSES, code="String toString() { return name; }")
    f = features.compute([c_miss, c_hit])
    assert f[1]["mentioned"] == 1.0 and f[0]["mentioned"] == 0.0
    assert f[1]["name_overlap"] == 1.0 and f[1]["body_similarity"] > f[0]["body_similarity"]
    assert features.tokens("parseHTTPValue_inner") == ["parse", "http", "inner"]
    from fl_tools.selection.candidates import BugCase
    case = BugCase("Lang-9", "Lang", "x", {"a.B::parseValue(String)"}, [c_miss, c_hit])
    order, info = selectors.get("S1").order(case)
    assert order[0]["method_name"] == "a.B::parseValue(String)" and "features" in info


def test_split_is_stratified_and_fixed():
    s1, s2 = make_split(), make_split()
    assert s1 == s2 and len(s1["dev"]) == 50 and len(s1["test"]) == 50
    assert not set(s1["dev"]) & set(s1["test"])
    projects = lambda names: {n.split("-")[0] for n in names}
    assert projects(s1["dev"]) == projects(s1["test"])


def test_replay_writes_runs_that_score_reads(tmp_path):
    run = _run(tmp_path, {
        "Lang-1": (["a.B::parseValue(String)"], [_m("a.B::toString()", 8, CAUSES), _m("a.B::parseValue(String)", 8, CAUSES)]),
        "Lang-2": (["x.Y::f()"], [_m("x.Y::f()", 9), _m("x.Y::g()", 3)]),
        "Lang-3": (["q.R::h()"], None),
    })
    assert len(load_cases(run)) == 3
    out = replay(run, ["S0", "S1"], split_path=None, out_root=str(tmp_path / "out"), draws=50)
    assert out["parts"]["all"]["source"]["top1"] == 1 and out["selectors"]["S1"]["parts"]["all"]["top1"] == 2
    sel_dir = str(tmp_path / "out" / "run-sel-S1")
    assert os.path.exists(os.path.join(sel_dir, "run_meta.json"))
    scored = score_run(sel_dir, write=False)
    assert "| ALL | 3 | 2 | 2 (67%) |" in scored["markdown"]       # crash still counts as attempted
    assert os.path.exists(str(tmp_path / "out" / "run-selection.md"))


def test_test_part_hidden_by_default(tmp_path):
    split = tmp_path / "split.json"
    split.write_text(json.dumps({"dev": ["Lang-1"], "test": ["Lang-2"]}))
    run = _run(tmp_path, {"Lang-1": (["x.Y::f()"], [_m("x.Y::f()", 9)]), "Lang-2": (["x.Y::f()"], [_m("x.Y::f()", 9)])})
    hidden = replay(run, ["S0"], split_path=str(split), write=False, draws=10)
    assert list(hidden["parts"]) == ["dev"] and hidden["test_hidden"]
    shown = replay(run, ["S0"], split_path=str(split), write=False, draws=10, reveal_test=True)
    assert list(shown["parts"]) == ["dev", "test", "all"]
