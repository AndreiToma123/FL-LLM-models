"""Ranking metrics over all attempted bugs (a bug without output or without the buggy method counts as a miss)."""
import random
from typing import Dict, List, Optional, Sequence

from ..ties import _groups
from .candidates import BugCase

KS = (1, 3, 5)


def first_rank(order: Sequence[dict], truth: set) -> Optional[int]:
    for i, m in enumerate(order, start=1):
        if m.get("method_name") in truth:
            return i
    return None


def average_precision(order: Sequence[dict], truth: set) -> float:
    """AP over all ground-truth methods; buggy methods missing from the list contribute 0 (as in FlexFL's MAP)."""
    if not truth:
        return 0.0
    hits, total = 0, 0.0
    for i, m in enumerate(order, start=1):
        if m.get("method_name") in truth:
            hits += 1
            total += hits / i
    return total / len(truth)


def evaluate(cases: List[BugCase], orders: Dict[str, List[dict]]) -> dict:
    """Top-1/3/5, MRR and MAP over all cases. orders: bug -> ranked candidates (missing = no output)."""
    n = len(cases)
    top = {k: 0 for k in KS}
    rr = ap = 0.0
    for case in cases:
        order = orders.get(case.bug, [])
        rank = first_rank(order, case.truth)
        for k in KS:
            top[k] += int(rank is not None and rank <= k)
        rr += 1.0 / rank if rank else 0.0
        ap += average_precision(order, case.truth)
    return {"n": n, "top1": top[1], "top3": top[3], "top5": top[5],
            "mrr": rr / n if n else 0.0, "map": ap / n if n else 0.0}


def oracle(cases: List[BugCase]) -> dict:
    """Best case for any tie-breaker: inside each tie group the buggy methods come first."""
    orders = {}
    for case in cases:
        out = []
        for g in _groups(case.candidates):
            out += sorted(g, key=lambda m: m.get("method_name") not in case.truth)
        orders[case.bug] = out
    return evaluate(cases, orders)


def random_ties(cases: List[BugCase], draws: int = 2000, seed: int = 0) -> dict:
    """Expected metrics when ties are ordered at random (the 'no information' reference, S0r)."""
    rng = random.Random(seed)
    sums = {"top1": [], "top3": [], "top5": [], "mrr": [], "map": []}
    for _ in range(draws):
        orders = {}
        for case in cases:
            out = []
            for g in _groups(case.candidates):
                g = list(g)
                rng.shuffle(g)
                out += g
            orders[case.bug] = out
        m = evaluate(cases, orders)
        for k in sums:
            sums[k].append(m[k])

    def summary(vals):
        vals = sorted(vals)
        return {"mean": sum(vals) / len(vals), "p2_5": vals[int(0.025 * (len(vals) - 1))],
                "p97_5": vals[int(round(0.975 * (len(vals) - 1)))]}
    return {k: summary(v) for k, v in sums.items()} | {"draws": draws, "seed": seed}
