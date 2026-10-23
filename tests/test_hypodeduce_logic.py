import json
import os
import sys

import pytest

from fl_tools.hypodeduce import logic
from fl_tools.hypodeduce.config import build_configs, prompts_digest
from fl_tools.runner import MetaMismatch, Runner, build_meta, check_or_write_meta


def test_parse_hypotheses_formats_and_limit():
    text = ("Some intro.\n**Hypothesis 1:** null pointer in A.f\nmore detail\n"
            "Hypothesis 2 - wrong loop bound in B.g\nHypothesis 3:  Wrong loop bound in  B.g\nHypothesis 4: x")
    assert logic.parse_hypotheses(text, 5) == ["null pointer in A.f\nmore detail", "wrong loop bound in B.g", "x"]
    assert logic.parse_hypotheses(text, 2) == ["null pointer in A.f\nmore detail", "wrong loop bound in B.g"]
    assert logic.parse_hypotheses("1. first cause\n2) second cause", 5) == ["first cause", "second cause"]
    assert logic.parse_hypotheses("no structure at all", 5) == []


def test_parse_ranked_classes_keeps_model_order_and_filters():
    known = {"a.B", "a.C", "a.D$E"}
    text = "1. #a.C#: x\n2. #a.Unknown#\n3. #a.B#\nalso a.D$E and a.C again"
    assert logic.parse_ranked_classes(text, known, 5) == ["a.C", "a.B", "a.D$E"]
    assert logic.parse_ranked_classes(text, known, 1) == ["a.C"]


def test_retention_is_union_over_hypotheses():
    per = {0: {"A": ["A::f()"], "B": []}, 1: {"A": ["A::g()", "A::f()"]}, 2: {}}
    union, support = logic.retain(per)
    assert union == {"A": ["A::f()", "A::g()"], "B": []}
    assert support == {"A::f()": [0, 1], "A::g()": [1]}


def test_selection_and_final_order():
    scores = {("A::f()", 0): 6, ("A::g()", 1): 9, ("A::f()", 1): 2, ("B::h()", 1): 9}
    selected, plaus = logic.select_hypothesis(3, scores, "max")
    assert selected == 1 and plaus[2] == (-1.0, -1.0)
    support = {"A::f()": [0, 1], "A::g()": [1], "B::h()": [1]}
    order = logic.final_order(["A::f()", "A::g()", "B::h()"], selected, support, scores)
    # selected hypothesis first (by its own score, ties in review order), f() scored 2 under it
    assert [m for m, _ in order] == ["A::g()", "B::h()", "A::f()"]
    assert order[2][1] == (1, 2.0)
    # ties between hypotheses go to the earlier one
    assert logic.select_hypothesis(2, {("x", 0): 5, ("y", 1): 5}, "max")[0] == 0
    assert logic.select_hypothesis(2, {}, "max")[0] is None
    with pytest.raises(ValueError):
        logic.plausibility([1], "bogus")


def test_mean_top3_rule_differs_from_max():
    scores = {("a", 0): 10, ("b", 0): 1, ("c", 0): 1, ("d", 1): 8, ("e", 1): 8, ("f", 1): 8}
    assert logic.select_hypothesis(2, scores, "max")[0] == 0
    assert logic.select_hypothesis(2, scores, "mean_top3")[0] == 1


def _fake_soapfl(tmp_path):
    d = tmp_path / "SoapFL" / "Config" / "Default"
    d.mkdir(parents=True)
    (d / "ChatChainConfig.json").write_text(json.dumps({"chain": [], "num_test_suites": 5}))
    phase = {"assistant_role_name": "R", "user_role_name": "R", "phase_prompt": ["p"]}
    (d / "PhaseConfig.json").write_text(json.dumps({"FindRelatedMethods": phase, "MethodReview": phase}))
    (d / "RoleConfig.json").write_text(json.dumps({"R": ["r"]}))
    return str(tmp_path / "SoapFL")


def test_build_configs_merges_with_soapfl_defaults(tmp_path):
    paths = build_configs(_fake_soapfl(tmp_path), str(tmp_path / "cfg"))
    assert all(os.path.basename(os.path.dirname(p)) == "HypoDeduce" for p in paths)
    chain = json.load(open(paths[0]))
    assert chain["num_test_suites"] == 5 and chain["chain"][1]["phase"] == "HypothesisGeneration"
    phases = json.load(open(paths[1]))
    assert phases["HypothesisMethodReview"] == phases["MethodReview"]
    assert "num_hypotheses" in "".join(phases["HypothesisGeneration"]["phase_prompt"])
    assert len(prompts_digest()) == 16


def test_runner_command_env_and_meta_for_hypodeduce(tmp_path, monkeypatch):
    soapfl = _fake_soapfl(tmp_path)
    monkeypatch.setenv("SOAPFL_HD_HYPOTHESES", "5")
    r = Runner(name="t", results_dir=str(tmp_path / "res"), soapfl_dir=soapfl, python=sys.executable,
               pipeline="hypodeduce", config="HypoDeduce", progress=lambda m: None, patches_dir=str(tmp_path))
    from fl_tools.bugs import parse_bugs
    bug = parse_bugs("Lang-1")[0]
    cmd = r._command(bug)
    assert cmd[1:3] == ["-m", "fl_tools.hypodeduce.soapfl_entry"] and "--config" in cmd
    env = r._env(bug)
    assert env["SOAPFL_HD_CONFIG_DIR"].endswith("_hypodeduce_config")
    assert os.path.dirname(os.path.dirname(os.path.abspath(__file__))) in env["PYTHONPATH"]
    meta = build_meta("t", soapfl, "HypoDeduce", "LOCAL", True, 0, str(tmp_path), "hypodeduce")
    assert meta["pipeline"] == "hypodeduce" and meta["llm_env"]["SOAPFL_HD_HYPOTHESES"] == "5"
    out = tmp_path / "meta"
    out.mkdir()
    check_or_write_meta(str(out), meta)
    monkeypatch.setenv("SOAPFL_HD_HYPOTHESES", "3")
    with pytest.raises(MetaMismatch):
        check_or_write_meta(str(out), build_meta("t", soapfl, "HypoDeduce", "LOCAL", True, 0, str(tmp_path),
                                                 "hypodeduce"))


def test_old_soapfl_meta_still_resumes(tmp_path):
    """run_meta.json files written before the pipeline field existed must count as 'soapfl'."""
    out = tmp_path / "old"
    out.mkdir()
    old = {"config": "Default", "model_type": "LOCAL", "lenient": True, "seed": 0, "llm_env": {}}
    (out / "run_meta.json").write_text(json.dumps(old))
    new = dict(old, pipeline="soapfl")
    check_or_write_meta(str(out), new)          # no MetaMismatch
    with pytest.raises(MetaMismatch):
        check_or_write_meta(str(out), dict(old, pipeline="hypodeduce"))


def test_existing_configs_are_reused_and_tmp_names_unique(tmp_path):
    from fl_tools.hypodeduce.config import existing_configs
    root = str(tmp_path / "cfg")
    assert existing_configs(root) is None
    paths = build_configs(_fake_soapfl(tmp_path), root)
    assert existing_configs(root) == paths
    assert not [f for f in os.listdir(os.path.dirname(paths[0])) if f.endswith(".tmp")]


def test_file_not_found_is_not_model_not_found():
    from fl_tools.runner import classify_failure
    assert classify_failure("FileNotFoundError: [Errno 2] No such file") != "model_not_found"
    assert classify_failure("openai.NotFoundError: Error code: 404") == "model_not_found"


def test_subset_of_draws_from_the_bigger_sample():
    from fl_tools.bugs import select_bugs
    big = {b.name for b in select_bugs("", 100, 0)}
    small = select_bugs("", 10, 0, subset_of=100)
    assert len(small) == 10 and all(b.name in big for b in small)
    assert len({b.project for b in small}) == 6


def test_compare_pairs_runs(tmp_path):
    from fl_tools.compare import compare_runs, mcnemar_exact
    def make(name, ranks):
        for bug, rank in ranks.items():
            d = tmp_path / name / f"d4j1.4.0-{bug}"
            d.mkdir(parents=True)
            methods = [{"method_name": f"m{i}", "class_name": "C", "score": 5} for i in range(1, 6)]
            (d / "result.json").write_text(json.dumps({"buggy_methods": methods}))
            (d / "ground_truth.json").write_text(json.dumps({"buggy_methods": [f"m{rank}"]}))
        return str(tmp_path / name)
    a = make("a", {"Lang-1": 1, "Lang-2": 1, "Lang-3": 4})
    b = make("b", {"Lang-1": 2, "Lang-2": 1, "Math-1": 1})
    c = compare_runs(a, b)
    assert c["common"] == 2 and c["top"][1] == {"a": 2, "b": 1, "only_a": 1, "only_b": 0, "p": 1.0}
    assert mcnemar_exact(16, 2) < 0.002
