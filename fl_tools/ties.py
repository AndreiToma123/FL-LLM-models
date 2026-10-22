"""RQ3 step 0: how much does SoapFL's final ranking depend on score ties?

Offline analysis of an existing run (no model calls). SoapFL ranks the reviewed methods with
``sorted(..., key=score, reverse=True)`` (chatdev/phase.py, MethodReview.execute). Python's sort is
stable, also with ``reverse=True``, so methods with equal scores keep the order in which they
were reviewed. ``result.json`` stores the list after that sort, therefore inside a tie group the
stored order IS the review order.

For every bug that has a ranking and a ground truth we compute, with the real review order
and with other orders of the same tie groups:

* best case   - buggy methods placed first inside their tie group (oracle tie-breaker)
* worst case  - buggy methods placed last inside their tie group
* actual      - the review order SoapFL really used
* reversed    - reverse review order inside each tie group
* random      - mean over many random orders inside tie groups (expected value, spread)

The gap best - worst is the most any tie-breaking rule could change Top-N on this run, given
the scores the model produced. Methods the model never scored (class missed, method filtered
out) are outside the reach of a tie-breaker; they are reported separately.
"""
import json
import os
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence

from .funnel import classify
from .results import BugRecord, load_records

KS = (1, 3, 5)


def _groups(ranked: List[dict]) -> List[List[dict]]:
    """Consecutive runs of equal scores (the list is already sorted by score)."""
    groups: List[List[dict]] = []
    for m in ranked:
        if groups and groups[-1][0].get("score") == m.get("score"):
            groups[-1].append(m)
        else:
            groups.append([m])
    return groups


def _hits(order: Sequence[dict], truth: set) -> Dict[int, bool]:
    names = [m.get("method_name") for m in order]
    return {k: any(n in truth for n in names[:k]) for k in KS}


def _first_rank(order: Sequence[dict], truth: set) -> Optional[int]:
    for i, m in enumerate(order, start=1):
        if m.get("method_name") in truth:
            return i
    return None


def _reorder(groups: List[List[dict]], how: str, truth: set, rng: Optional[random.Random] = None) -> List[dict]:
    out: List[dict] = []
    for g in groups:
        g = list(g)
        if how == "best":
            g.sort(key=lambda m: m.get("method_name") not in truth)   # stable: truth first
        elif how == "worst":
            g.sort(key=lambda m: m.get("method_name") in truth)       # stable: truth last
        elif how == "reversed":
            g.reverse()
        elif how == "random":
            rng.shuffle(g)
        out.extend(g)
    return out


def analyse_bug(record: BugRecord) -> Optional[dict]:
    """Per-bug facts, or None if the bug has no usable ranking/ground truth."""
    if not record.result or not record.truth:
        return None
    ranked = record.result.get("buggy_methods", [])
    if not ranked:
        return None
    truth = set(record.truth)
    groups = _groups(ranked)
    names = [m.get("method_name") for m in ranked]
    in_ranking = any(n in truth for n in names)
    info = {
        "bug": record.bug.name, "project": record.bug.project, "n_scored": len(ranked),
        "stage": classify(record)["stage"], "buggy_in_ranking": in_ranking,
        "top_score": ranked[0].get("score"),
        "top_group_size": len(groups[0]),
        "n_distinct_scores": len(groups),
        "scores": [m.get("score") for m in ranked],
    }
    if in_ranking:
        best_rank_actual = _first_rank(ranked, truth)
        buggy_score = ranked[best_rank_actual - 1].get("score")
        tie_size = sum(1 for m in ranked if m.get("score") == buggy_score)
        info.update({
            "actual_rank": best_rank_actual, "buggy_score": buggy_score, "tie_size": tie_size,
            "in_tie": tie_size > 1,
            "n_truth_in_ranking": sum(1 for n in names if n in truth),
        })
    return info


def analyse_run(run_dir: str, soapfl_dir: Optional[str] = None, draws: int = 2000, seed: int = 0,
                write: bool = True) -> dict:
    records = load_records(run_dir, soapfl_dir)
    all_infos = [classify(r) for r in records]
    n_attempted = len(records)
    infra = {i["bug"] for i in all_infos if i["stage"] in
             ("crashed", "not_run", "context_overflow")}

    per_bug = []
    usable: List[tuple] = []
    for r in records:
        info = analyse_bug(r)
        if info is not None:
            per_bug.append(info)
            usable.append((r, info))

    rng = random.Random(seed)
    scenario = {s: Counter() for s in ("actual", "best", "worst", "reversed")}
    for r, info in usable:
        truth = set(r.truth)
        groups = _groups(r.result["buggy_methods"])
        for s in scenario:
            order = r.result["buggy_methods"] if s == "actual" else _reorder(groups, s, truth)
            for k, hit in _hits(order, truth).items():
                scenario[s][k] += int(hit)

    # order sensitivity: random order inside tie groups, many draws
    totals = {k: [] for k in KS}
    mrr_draws: List[float] = []
    for _ in range(draws):
        t = Counter()
        rr = 0.0
        for r, info in usable:
            truth = set(r.truth)
            order = _reorder(_groups(r.result["buggy_methods"]), "random", truth, rng)
            for k, hit in _hits(order, truth).items():
                t[k] += int(hit)
            fr = _first_rank(order, truth)
            rr += 1.0 / fr if fr else 0.0
        for k in KS:
            totals[k].append(t[k])
        mrr_draws.append(rr)

    def spread(values: List[float]) -> dict:
        values = sorted(values)
        n = len(values)
        return {"mean": sum(values) / n, "min": values[0], "max": values[-1],
                "p2_5": values[int(0.025 * (n - 1))], "p97_5": values[int(round(0.975 * (n - 1)))]}

    reached = [i for i in per_bug if i["buggy_in_ranking"]]
    tied = [i for i in reached if i["in_tie"]]
    top1_actual = [i for i in reached if i["actual_rank"] == 1]
    top1_tied = [i for i in top1_actual if i["in_tie"]]
    top_group_multi = [i for i in per_bug if i["top_group_size"] > 1]
    score_hist = Counter(s for i in per_bug for s in i["scores"])
    top_hist = Counter(i["top_score"] for i in per_bug)

    summary = {
        "run": os.path.basename(os.path.normpath(run_dir)),
        "attempted": n_attempted,
        "infrastructure_failures": len(infra),
        "with_ranking_and_truth": len(per_bug),
        "buggy_method_in_ranking": len(reached),
        "buggy_in_tie_group": len(tied),
        "top1_actual": len(top1_actual),
        "top1_actual_that_are_tied": len(top1_tied),
        "bugs_where_top_score_group_has_several_methods": len(top_group_multi),
        "scenario_counts": {s: dict(c) for s, c in scenario.items()},
        "random_order": {f"top{k}": spread(totals[k]) for k in KS},
        "random_order_mrr_sum": spread(mrr_draws),
        "draws": draws, "seed": seed,
        "score_histogram": dict(sorted(score_hist.items())),
        "top_score_histogram": dict(sorted(top_hist.items(), key=lambda kv: (kv[0] is None, kv[0]))),
        "mean_methods_scored": (sum(i["n_scored"] for i in per_bug) / len(per_bug)) if per_bug else 0,
    }
    markdown = format_markdown(summary, per_bug)
    written: List[str] = []
    if write:
        with open(os.path.join(run_dir, "ties.md"), "w", encoding="utf-8") as f:
            f.write(markdown + "\n")
        with open(os.path.join(run_dir, "ties.json"), "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "per_bug": per_bug}, f, indent=2)
        written = [os.path.join(run_dir, "ties.md"), os.path.join(run_dir, "ties.json")]
    return {"summary": summary, "per_bug": per_bug, "markdown": markdown, "written": written}


def format_markdown(s: dict, per_bug: List[dict]) -> str:
    sc = s["scenario_counts"]
    n = s["with_ranking_and_truth"]

    def row(name, c):
        return f"| {name} | {c.get(1, 0)} | {c.get(3, 0)} | {c.get(5, 0)} |"

    ro = s["random_order"]
    lines = [
        f"## Tie and selection analysis: {s['run']}", "",
        "Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.", "",
        f"* bugs attempted: {s['attempted']} (infrastructure failures: {s['infrastructure_failures']})",
        f"* bugs with a ranking and a ground truth: {n}",
        f"* buggy method present in the ranking (reachable by any tie-breaker): {s['buggy_method_in_ranking']}",
        f"* of those, buggy method shares its score with another method: {s['buggy_in_tie_group']}",
        f"* Top-1 hits: {s['top1_actual']}; of these tied with another method: {s['top1_actual_that_are_tied']}",
        f"* bugs whose highest score is shared by several methods: {s['bugs_where_top_score_group_has_several_methods']} of {n}",
        f"* mean number of scored methods per bug: {s['mean_methods_scored']:.1f}", "",
        "### Top-N under different orders inside tie groups (counts of bugs)", "",
        "| Order inside tie groups | Top-1 | Top-3 | Top-5 |", "|---|---:|---:|---:|",
        row("actual (SoapFL review order)", sc["actual"]),
        row("reversed review order", sc["reversed"]),
        row("worst case (buggy method last in its tie)", sc["worst"]),
        row("best case (buggy method first in its tie) = oracle tie-breaker", sc["best"]),
        f"| random (mean of {s['draws']} draws) | {ro['top1']['mean']:.1f} | {ro['top3']['mean']:.1f} | {ro['top5']['mean']:.1f} |",
        f"| random, 95% range | {ro['top1']['p2_5']}-{ro['top1']['p97_5']} | {ro['top3']['p2_5']}-{ro['top3']['p97_5']} "
        f"| {ro['top5']['p2_5']}-{ro['top5']['p97_5']} |", "",
        f"Reading: with the model's scores unchanged, Top-1 can range from {sc['worst'].get(1, 0)} (worst) to "
        f"{sc['best'].get(1, 0)} (best) out of {s['attempted']} attempted bugs, only by reordering equal scores. "
        f"Reachable ceiling for any selection rule on this run: {s['buggy_method_in_ranking']} "
        f"(buggy method scored at all).", "",
        "### Score scale actually used (all scored methods)", "",
        "| Score | Methods |", "|---:|---:|",
    ]
    for score, count in s["score_histogram"].items():
        lines.append(f"| {score} | {count} |")
    lines += ["", "### Highest score per bug", "", "| Top score | Bugs |", "|---:|---:|"]
    for score, count in s["top_score_histogram"].items():
        lines.append(f"| {score} | {count} |")
    return "\n".join(lines)
