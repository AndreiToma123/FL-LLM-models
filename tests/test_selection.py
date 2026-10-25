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


# ---------------------------------------------------------------- model-based selectors (mock endpoint)
import pytest

from fl_tools.mock_server import start_mock_server
from fl_tools.selection import judges, prompts
from fl_tools.selection.candidates import BugCase
from fl_tools.selection.llm import JudgeClient, JudgeError, probe_logprobs

PAIR_RULES = [
    {"match": r"Method A: B::parseValue", "reply": "A"},
    {"match": r"Method B: B::parseValue", "reply": "B"},
    {"match": r"Method M: B::parseValue", "reply": "7", "logprobs": {"7": -0.3, "8": -1.5, "2": -3.0}},
    {"match": r"Method M: B::toString", "reply": "7", "logprobs": {"7": -0.2, "2": -1.8, "1": -3.0}},
    {"match": r"Method M: B::other", "reply": "5", "logprobs": {"5": -0.1, "1": -2.5}},
    {"match": r"how many sides", "reply": "3", "logprobs": {"3": -0.01, "4": -5.0}},
]


def _cands():
    return [_m("a.B::toString()", 8, CAUSES, code="String toString() { return n; }"),
            _m("a.B::other()", 8, CAUSES, code="void other() {}"),
            _m("a.B::parseValue(String)", 8, CAUSES, code="int parseValue(String s) { return n; }"),
            _m("a.B::low()", 3, CAUSES)]


@pytest.fixture
def server():
    srv = start_mock_server(rules=PAIR_RULES, reply="A")
    yield srv
    srv.stop()


def test_s5_pairwise_both_orders_and_copeland(server, tmp_path):
    client = JudgeClient("mock-model", base_url=server.url, cache_path=str(tmp_path / "c.jsonl"))
    case = BugCase("Lang-1", "Lang", "x", {"a.B::parseValue(String)"}, _cands())
    order, info = judges.S5().configure(client).order(case)
    assert order[0]["method_name"] == "a.B::parseValue(String)" and order[-1]["method_name"] == "a.B::low()"
    assert info["pairs"] == 3 and info["calls"] == 6            # 3 pairs x 2 orders, low() not shortlisted
    # toString vs other: the mock answers "A" in both orders -> position bias -> a draw, not a win
    assert info["draws"] == 1 and info["position_inconsistent"] == 1
    again = judges.S5().configure(JudgeClient("mock-model", base_url=server.url, cache_path=str(tmp_path / "c.jsonl")))
    assert again.order(case)[1]["calls"] == 0                   # all from the cache


def test_s2_expected_score_and_s5s2_breaks_draws(server):
    client = JudgeClient("mock-model", base_url=server.url)
    case = BugCase("Lang-1", "Lang", "x", {"a.B::parseValue(String)"}, _cands())
    order, info = judges.S2().configure(client).order(case)
    exp = info["expected_score"]
    assert exp["a.B::parseValue(String)"] > exp["a.B::toString()"] > exp["a.B::other()"]
    assert order[0]["method_name"] == "a.B::parseValue(String)"
    order, info = judges.S5S2().configure(client).order(case)
    # pairwise: parseValue +2, toString and other tied at -1 -> S2 only for those two
    assert set(info["expected_score"]) == {"a.B::toString()", "a.B::other()"}
    assert [m["method_name"] for m in order[:3]] == ["a.B::parseValue(String)", "a.B::toString()", "a.B::other()"]


def test_s2_without_logprobs_fails_clearly(tmp_path):
    srv = start_mock_server(reply="7")
    try:
        client = JudgeClient("mock-model", base_url=srv.url)
        assert probe_logprobs(client)["supported"] is False
        with pytest.raises(JudgeError, match="log-probabilities"):
            judges.S2().configure(client).order(BugCase("Lang-1", "Lang", "x", set(), _cands()))
    finally:
        srv.stop()


def test_top_k_shortlist_crosses_hypothesis_tiers():
    c = [dict(_m("x::sel1()", 9), rank_key=[1, 9]), dict(_m("x::sel2()", 9), rank_key=[1, 9]),
         dict(_m("x::bug()", 8, ), rank_key=[0, 8], scores_by_hypothesis={"h1": 3, "h2": 10}),
         dict(_m("x::far()", 1), rank_key=[0, 1])]
    head, rest = judges.shortlist(c, "top-tie", 8)
    assert head == [0, 1] and rest == [2, 3]                     # bug() unreachable for a tie-breaker
    head, rest = judges.shortlist(c, "top-k", 3)
    assert head == [2, 0, 1] and rest == [3]


def test_replay_with_judge_hides_test_and_reports_cost(server, tmp_path):
    split = tmp_path / "split.json"
    split.write_text(json.dumps({"dev": ["Lang-1"], "test": ["Lang-2"]}))
    truth = ["a.B::parseValue(String)"]
    run = _run(tmp_path, {"Lang-1": (truth, _cands()), "Lang-2": (truth, _cands())})
    client = JudgeClient("mock-model", base_url=server.url)
    out = replay(run, ["S5"], split_path=str(split), out_root=str(tmp_path / "out"), draws=20, client=client)
    dev = out["selectors"]["S5"]["parts"]["dev"]
    assert dev["top1"] == 1 and dev["cost"]["bugs_judged"] == 1 and dev["cost"]["calls"] == 6
    assert client.stats["calls"] == 6                            # test bug Lang-2 not judged while hidden
    meta = json.load(open(tmp_path / "out" / "run-sel-S5" / "run_meta.json"))
    assert meta["selection"]["judged_parts"] == ["dev"] and meta["selection"]["prompt_version"] == prompts.version()
    assert "Top-1 reachable in shortlist" in out["markdown"]
    with pytest.raises(ValueError, match="model calls"):
        replay(run, ["S2"], split_path=str(split), write=False, draws=10)


def test_parse_choice_and_short_name():
    assert prompts.parse_choice(" b.") == "B" and prompts.parse_choice("Answer: A") == "A"
    assert prompts.parse_choice("neither") is None
    assert prompts.short_name("org.a.Foo$Bar::baz(int)") == "Foo$Bar::baz(int)"


def test_summary_keeps_earlier_selectors(tmp_path):
    run = _run(tmp_path, {"Lang-1": (["x.Y::f()"], [_m("x.Y::g()", 9), _m("x.Y::f()", 9)])})
    replay(run, ["S0", "S1"], split_path=None, out_root=str(tmp_path / "o"), draws=10)
    out = replay(run, ["S1-body"], split_path=None, out_root=str(tmp_path / "o"), draws=10)
    assert list(out["selectors"]) == ["S0", "S1", "S1-body"] and "| S1 |" in out["markdown"]


# ---------------------------------------------------------------- failure-context selectors S6, S8a, S8b
from fl_tools.selection import agent

CTX = {"failing_tests_total": 1, "tests": [{
    "name": "a.BTest::testParse", "output": "bad sign",
    "stack_trace": ["--- a.BTest::testParse", "java.lang.NumberFormatException: bad sign",
                    "\tat a.B.parseValue(B.java:12)", "\tat a.BTest.testParse(BTest.java:7)"],
    "frames": [{"class": "a.B", "method": "parseValue", "line": 12, "key": "a.B::parseValue"},
               {"class": "a.BTest", "method": "testParse", "line": 7, "key": "a.BTest::testParse"}],
    "test_method": {"class": "a.BTest", "signature": "testParse()", "code": "void testParse() { B.parseValue(\"-1\"); }"},
    "covered_methods": ["a.B::parseValue(String)", "a.B::toString()"]}],
    "methods": {"a.B::parseValue(String)": {"failing_tests_covering": 1, "stack_depth": 0},
                "a.B::toString()": {"failing_tests_covering": 1, "stack_depth": None}},
    "method_code": {"a.B::helper()": {"code": "int helper() { return 1; }", "doc": ""}}}


def _case_ctx(ctx=CTX):
    return BugCase("Lang-1", "Lang", "x", {"a.B::parseValue(String)"}, _cands(), context=ctx)


def test_s6_stack_tiebreak_without_model():
    order, info = selectors.get("S6").order(_case_ctx())
    assert order[0]["method_name"] == "a.B::parseValue(String)" and order[-1]["method_name"] == "a.B::low()"
    assert selectors.get("S6").order(_case_ctx(None))[1] == {"no_context": True}


def test_s8a_prompt_carries_evidence_and_skips_bugs_without_context(server):
    client = JudgeClient("mock-model", base_url=server.url)
    sel = judges.S8a().configure(client)
    order, info = sel.order(_case_ctx())
    assert order[0]["method_name"] == "a.B::parseValue(String)"
    sent = [m["messages"][1]["content"] for m in server.requests if "Evidence:" in m["messages"][1]["content"]]
    assert any("on the stack trace of a failing test at depth 0" in t for t in sent)
    assert all("Failing test a.BTest::testParse" in t and "not on the stack trace" in t for t in sent)
    assert "a.B" not in prompts.short_name("a.B::f()").split("::")[0][:-1]     # package dropped
    n = len(server.requests)
    order, info = sel.order(_case_ctx(None))
    assert info["no_context"] and len(server.requests) == n                 # no calls without context


AGENT_RULES = [
    {"match_last": r"Step limit reached", "tool_calls": [{"name": "submit_ranking", "arguments": {"ranking": ["C2"]}}]},
    {"match_last": r"C3: B::parseValue", "tool_calls": [{"name": "get_coverage", "arguments": {"label": "C3"}}]},
    {"match_last": r"C1: B::parseValue", "tool_calls": [{"name": "get_coverage", "arguments": {"label": "C1"}}]},
    {"match_last": r"^C3 B::parseValue.*depth 0", "tool_calls": [{"name": "submit_ranking", "arguments": {"ranking": ["C3"]}}]},
    {"match_last": r"^C1 B::parseValue.*depth 0", "tool_calls": [{"name": "submit_ranking", "arguments": {"ranking": ["C1"]}}]},
]


def test_s8b_native_tool_loop_forward_and_reversed(tmp_path):
    srv = start_mock_server(rules=AGENT_RULES)
    try:
        client = JudgeClient("mock-model", base_url=srv.url, cache_path=str(tmp_path / "c.jsonl"))
        sel = agent.S8b().configure(client, max_steps=6)
        order, info = sel.order(_case_ctx())
        assert order[0]["method_name"] == "a.B::parseValue(String)" and info["top1_agree"]
        assert info["tool_calls"] == 2 and info["calls"] == 4 and not info.get("invalid_actions")
        assert srv.requests[0]["tools"] and srv.requests[1]["messages"][-1]["role"] == "tool"
        again = agent.S8b().configure(JudgeClient("mock-model", base_url=srv.url, cache_path=str(tmp_path / "c.jsonl")))
        assert again.order(_case_ctx())[1]["calls"] == 0                  # whole loop replayed from cache
    finally:
        srv.stop()


def test_s8b_json_protocol_and_step_cap():
    rules = [{"match_last": r"Step limit reached", "reply": '{"tool": "submit_ranking", "args": {"ranking": ["C2", "C1"]}}'},
             {"match_last": r".", "reply": '{"tool": "list_failing_tests", "args": {}}'}]
    srv = start_mock_server(rules=rules)
    try:
        sel = agent.S8b().configure(JudgeClient("mock-model", base_url=srv.url), max_steps=3, protocol="json")
        order, info = sel.order(_case_ctx())
        assert info["tool_calls"] == 6 and info["forced_submit"] == 2       # 3 per run, forward + reversed
        assert "tools" not in srv.requests[0] and "JSON object" in srv.requests[0]["messages"][0]["content"]
        # forward: C2 = other(); reversed: C2 = other() as well (3 candidates) -> other() first
        assert order[0]["method_name"] == "a.B::other()"
    finally:
        srv.stop()


def test_agent_tools_never_expose_truth_or_source_score():
    labelled = {"C1": dict(_cands()[2], reason="LEAK reason", score=8)}
    t = agent.Tools(CTX, labelled)
    for name, args in [("list_failing_tests", {}), ("get_test", {"index": 1}), ("get_stack_trace", {"index": 1}),
                       ("get_candidate", {"label": "C1"}), ("get_coverage", {"label": "c1"}),
                       ("search_methods", {"query": "parse"}), ("get_method_code", {"method": "B::helper()"})]:
        answer, valid = t.call(name, args)
        assert valid and "LEAK" not in answer, name
    assert t.call("get_test", {"index": 9})[1] is False and t.call("nope", {})[1] is False
    assert agent.parse_ranking("C2 > c1", ["C1", "C2", "C3"]) == ["C2", "C1", "C3"]
    assert agent.parse_json_action('ok {"tool": "get_test", "args": {"index": 1}}') == ("get_test", {"index": 1})


def test_gate_scores_policies_offline(server, tmp_path):
    from fl_tools.selection.gate import gate
    truth = ["a.B::parseValue(String)"]
    run = _run(tmp_path, {"Lang-1": (truth, _cands()), "Lang-2": (["x.Y::f()"], [_m("x.Y::f()", 9), _m("x.Y::g()", 3)])})
    client = JudgeClient("mock-model", base_url=server.url)
    replay(run, ["S1", "S5"], split_path=None, out_root=str(tmp_path / "out"), draws=10, client=client)
    out = gate(run, ["S1", "S5"], split_path=None, out_root=str(tmp_path / "out"))
    rows = {r["policy"]: r for r in out["parts"]["all"]["rows"]}
    assert set(rows) == {"S0", "S0 > S1", "S0 > S5", "S0 > S1 > S5"}
    assert rows["S0"]["calls"] == 0 and rows["S0 > S5"]["calls"] == 6 and rows["S0 > S5"]["top1"] == 2
    # S1 is "always confident", so S0 > S1 > S5 never reaches S5
    assert rows["S0 > S1 > S5"]["calls"] == 0 and rows["S0 > S1"]["pareto"] and not rows["S0 > S5"]["pareto"]
    assert os.path.exists(str(tmp_path / "out" / "run-gate.md"))


def test_s8b_accepts_tool_calls_written_as_text_and_stops_after_two_invalid():
    # Qwen-style: the endpoint returns the tool call as text, not as a native tool call
    rules = [{"match_last": r"C3: B::parseValue", "reply": '<tool_call>\n{"name": "get_coverage", "arguments": {"label": "C3"}}\n</tool_call>'},
             {"match_last": r"C1: B::parseValue", "reply": '```json\n{"name": "get_coverage", "arguments": "{\\"label\\": \\"C1\\"}"}\n```'},
             {"match_last": r"RESULT of get_coverage:\nC3 B::parseValue", "reply": '{"name": "submit_ranking", "arguments": {"ranking": ["C3"]}}'},
             {"match_last": r"RESULT of get_coverage:\nC1 B::parseValue", "reply": '{"function": {"name": "submit_ranking", "arguments": {"ranking": ["C1"]}}}'}]
    srv = start_mock_server(rules=rules)
    try:
        order, info = agent.S8b().configure(JudgeClient("mock-model", base_url=srv.url)).order(_case_ctx())
        assert order[0]["method_name"] == "a.B::parseValue(String)" and info["tool_calls"] == 2 and info["top1_agree"]
    finally:
        srv.stop()
    srv = start_mock_server(reply="I think the bug is somewhere in the parser.")
    try:
        order, info = agent.S8b().configure(JudgeClient("mock-model", base_url=srv.url)).order(_case_ctx())
        assert info["forced_submit"] == 2 and info["steps"] == 6 and len(info["invalid_samples"]) == 2
        assert info["failed_runs"] == ["forward", "reversed"] and order == _cands()
    finally:
        srv.stop()


def test_summary_tolerates_rows_from_older_versions(server, tmp_path):
    run = _run(tmp_path, {"Lang-1": (["a.B::parseValue(String)"], _cands())})
    out_root = tmp_path / "o"
    client = JudgeClient("mock-model", base_url=server.url)
    replay(run, ["S5"], split_path=None, out_root=str(out_root), draws=10, client=client)
    js = out_root / "run-selection.json"
    old = json.loads(js.read_text())
    for k in ("no_context", "steps", "tool_calls"):
        old["selectors"]["S5"]["parts"]["all"]["cost"].pop(k)
    js.write_text(json.dumps(old))
    out = replay(run, ["S6"], split_path=None, out_root=str(out_root), draws=10, client=client)
    assert "| S5 |" in out["markdown"] and "| S6 |" in out["markdown"]
