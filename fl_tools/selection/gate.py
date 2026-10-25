"""B: confidence-gated escalation, scored OFFLINE from selector runs that already exist (no new model calls).

A policy is a ladder, e.g. S0 > S5 > S8b: start with the source order; if the top is not tied, stop; otherwise
use the next selector's order, and stop there if that selector is confident; else go on. The cost of a bug is
the model calls of every selector it reached (new + cached calls, i.e. what a fresh run would make).

Confidence of a step (from what the selector logged per bug):
  S0              top score not tied (or fewer than 2 candidates)
  S5, S8a         one candidate holds the highest Copeland score
  S2, S8a-lp      expected score of the first minus the second >= --margin (default 0.5)
  S5+S2, S8a+S2   unique Copeland top, or the S2 margin among the tied
  S8b             forward and reversed investigations agree on the top candidate
  S6              its key of the first is strictly larger than that of the second
  others (S1...)  always confident
The last step of a ladder is final. All ordered sub-ladders of --ladder are scored, plus "always X".
Choose a policy on dev; report the test part once (--reveal-test), like the selectors.
"""
import json
import os
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from ..ties import _groups
from . import metrics
from .candidates import BugCase, load_cases
from .split import DEFAULT_SPLIT, load_split, part_of


def load_selector_run(run_dir: str, name: str, out_root: Optional[str] = None) -> Dict[str, Tuple[list, dict]]:
    run = os.path.basename(os.path.normpath(run_dir))
    base = os.path.join(out_root or os.path.dirname(os.path.normpath(run_dir)), f"{run}-sel-{name}", "bugs")
    if not os.path.isdir(base):
        raise FileNotFoundError(f"no replay of {name} found ({base}); run `select {run_dir} --selector {name}` first")
    out = {}
    for d in os.listdir(base):
        path = os.path.join(base, d, "result.json")
        if os.path.exists(path):
            res = json.load(open(path, encoding="utf-8"))
            bug = d.split("-", 1)[1]
            out[bug] = (res.get("buggy_methods") or [], res.get("selection") or {})
    return out


def _second_gap(values: List[float]) -> float:
    v = sorted(values, reverse=True)
    return v[0] - v[1] if len(v) > 1 else float("inf")


def confident(name: str, info: dict, order: list, margin: float) -> bool:
    if info.get("not_judged") or info.get("no_context"):
        return False
    if name in ("S5", "S8a"):
        cope = list((info.get("copeland") or {}).values())
        return bool(cope) and sorted(cope, reverse=True)[:2].count(max(cope)) == 1
    if name in ("S2", "S8a-lp"):
        return _second_gap(list((info.get("expected_score") or {}).values())) >= margin
    if name in ("S5+S2", "S8a+S2"):
        cope = list((info.get("copeland") or {}).values())
        if cope and sorted(cope, reverse=True)[:2].count(max(cope)) == 1:
            return True
        exp = list((info.get("expected_score") or {}).values())
        return len(exp) > 1 and _second_gap(exp) >= margin
    if name == "S8b":
        return bool(info.get("top1_agree"))
    if name == "S6":
        keys = info.get("keys") or {}
        if len(order) < 2:
            return True
        a, b = keys.get(order[0]["method_name"]), keys.get(order[1]["method_name"])
        return a is not None and b is not None and tuple(a) > tuple(b)
    return True


def cost(info: dict) -> Tuple[int, int]:
    return (int(info.get("calls", 0) or 0) + int(info.get("cached_calls", 0) or 0), int(info.get("tokens", 0) or 0))


def apply_policy(case: BugCase, ladder: List[str], runs: Dict[str, dict], margin: float):
    """(order, calls, tokens, last step used)."""
    cands = case.candidates
    groups = _groups(cands) if cands else []
    if len(cands) < 2 or not groups or len(groups[0]) < 2 or not ladder:
        return list(cands), 0, 0, "S0"
    calls = tokens = 0
    order, used = list(cands), "S0"
    for i, name in enumerate(ladder):
        got = runs[name].get(case.bug)
        if got is None:
            continue
        order, info = got
        c, t = cost(info)
        calls, tokens, used = calls + c, tokens + t, name
        if i == len(ladder) - 1 or confident(name, info, order, margin):
            break
    return order, calls, tokens, used


def sub_ladders(ladder: List[str]) -> List[List[str]]:
    out = [[]]
    for n in range(1, len(ladder) + 1):
        out += [list(c) for c in combinations(ladder, n)]
    return out


def gate(run_dir: str, ladder: List[str], margin: float = 0.5, split_path: Optional[str] = DEFAULT_SPLIT,
         reveal_test: bool = False, out_root: Optional[str] = None, soapfl_dir: Optional[str] = None,
         write: bool = True) -> dict:
    cases = load_cases(run_dir, soapfl_dir)
    runs = {name: load_selector_run(run_dir, name, out_root) for name in ladder}
    split = load_split(split_path) if split_path and os.path.exists(split_path) else None
    parts = (["dev", "test", "all"] if reveal_test else ["dev"]) if split else ["all"]
    report = {"run": os.path.basename(os.path.normpath(run_dir)), "ladder": ladder, "margin": margin,
              "parts": {}, "test_hidden": bool(split) and not reveal_test}
    for part in parts:
        sub = [c for c in cases if part == "all" or split is None or part_of(c.bug, split) == part]
        rows = []
        for lad in sub_ladders(ladder):
            orders, calls, tokens, used = {}, 0, 0, {}
            for c in sub:
                if not c.candidates:
                    continue
                o, cl, tk, u = apply_policy(c, lad, runs, margin)
                orders[c.bug], calls, tokens = o, calls + cl, tokens + tk
                used[u] = used.get(u, 0) + 1
            m = metrics.evaluate(sub, orders)
            rows.append({"policy": " > ".join(["S0"] + lad), "top1": m["top1"], "top3": m["top3"], "mrr": m["mrr"],
                         "calls": calls, "calls_per_bug": round(calls / max(1, len(sub)), 1), "tokens": tokens,
                         "stopped_at": used})
        best = {}
        for r in sorted(rows, key=lambda r: (r["calls"], -r["top1"])):       # Pareto front: Top-1 vs calls
            if not best or r["top1"] > max(b["top1"] for b in best.values()):
                best[r["policy"]] = r
        for r in rows:
            r["pareto"] = r["policy"] in best
        report["parts"][part] = {"n": len(sub), "rows": rows}
    report["markdown"] = format_markdown(report)
    if write:
        base = os.path.join(out_root or os.path.dirname(os.path.normpath(run_dir)), f"{report['run']}-gate")
        with open(base + ".md", "w", encoding="utf-8") as f:
            f.write(report["markdown"] + "\n")
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in report.items() if k != "markdown"}, f, indent=2)
        report["written"] = [base + ".md", base + ".json"]
    return report


def format_markdown(r: dict) -> str:
    lines = [f"## Gated escalation on {r['run']} (offline from cached selector runs; margin {r['margin']})", "",
             "Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). "
             "Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.", ""]
    for part, p in r["parts"].items():
        lines += [f"### {part} ({p['n']} bugs)", "",
                  "| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |",
                  "|---|---:|---:|---:|---:|---:|---|:-:|"]
        for row in sorted(p["rows"], key=lambda x: (x["calls"], -x["top1"])):
            stops = ", ".join(f"{k} {v}" for k, v in sorted(row["stopped_at"].items()))
            lines.append(f"| {row['policy']} | {row['top1']} | {row['top3']} | {row['mrr']:.3f} | {row['calls']} | "
                         f"{row['calls_per_bug']} | {stops} | {'*' if row['pareto'] else ''} |")
        lines.append("")
    if r.get("test_hidden"):
        lines.append("Test part hidden: choose the policy on dev, then run once with --reveal-test.")
    return "\n".join(lines)
