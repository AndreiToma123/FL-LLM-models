"""Compare two runs on the bugs they have in common (paired): Top-N, McNemar test, cost.

    python -m fl_tools compare reports/run100-qwen25coder reports/run10of100-qwen25coder-hd-h5c5m3

Only bugs that both runs attempted are counted, so a 10-bug run can be compared with the matching 10 bugs
of a 100-bug run. Infrastructure failures (crashes without a model answer) are listed separately.
"""
import os
from math import comb
from typing import Dict, List, Optional

from .funnel import classify
from .results import BugRecord, load_records

KS = (1, 3, 5)
INFRA = {"crashed", "not_run", "context_overflow"}


def _rank(record: BugRecord) -> Optional[int]:
    if not record.result or not record.truth:
        return None
    truth = set(record.truth)
    for i, m in enumerate(record.result.get("buggy_methods", []), start=1):
        if m.get("method_name") in truth:
            return i
    return None


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pairs."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def _cost(record: BugRecord) -> Dict[str, float]:
    calls = record.llm_calls
    tokens = sum((c.get("prompt_tokens") or 0) + (c.get("completion_tokens") or 0) for c in calls)
    return {"calls": len(calls), "tokens": tokens, "wall_s": float((record.run or {}).get("wall_s") or 0)}


def compare_runs(run_a: str, run_b: str, soapfl_dir: Optional[str] = None) -> dict:
    a = {r.bug.name: r for r in load_records(run_a, soapfl_dir)}
    b = {r.bug.name: r for r in load_records(run_b, soapfl_dir)}
    common = sorted(set(a) & set(b), key=lambda n: (n.split("-")[0], int(n.split("-")[1])))
    rows, infra = [], []
    for name in common:
        sa, sb = classify(a[name])["stage"], classify(b[name])["stage"]
        if sa in INFRA or sb in INFRA:
            infra.append((name, sa, sb))
        rows.append({"bug": name, "rank_a": _rank(a[name]), "rank_b": _rank(b[name]), "stage_a": sa,
                     "stage_b": sb, "cost_a": _cost(a[name]), "cost_b": _cost(b[name])})
    paired = [r for r in rows if r["stage_a"] not in INFRA and r["stage_b"] not in INFRA]
    tops = {}
    for k in KS:
        hit_a = [r["rank_a"] is not None and r["rank_a"] <= k for r in paired]
        hit_b = [r["rank_b"] is not None and r["rank_b"] <= k for r in paired]
        only_a = sum(1 for x, y in zip(hit_a, hit_b) if x and not y)
        only_b = sum(1 for x, y in zip(hit_a, hit_b) if y and not x)
        tops[k] = {"a": sum(hit_a), "b": sum(hit_b), "only_a": only_a, "only_b": only_b,
                   "p": mcnemar_exact(only_a, only_b)}

    def mean(key, side):
        vals = [r[f"cost_{side}"][key] for r in paired]
        return sum(vals) / len(vals) if vals else 0.0

    return {"a": os.path.basename(os.path.normpath(run_a)), "b": os.path.basename(os.path.normpath(run_b)),
            "common": len(common), "paired": len(paired), "infra": infra, "rows": rows, "top": tops,
            "cost": {side: {k: mean(k, side) for k in ("calls", "tokens", "wall_s")} for side in ("a", "b")}}


def format_markdown(c: dict) -> str:
    lines = [f"## {c['a']} (A) vs {c['b']} (B)", "",
             f"Bugs in both runs: {c['common']}; compared (no infrastructure failure in either): {c['paired']}.", "",
             "| | A | B | only A | only B | McNemar p |", "|---|---:|---:|---:|---:|---:|"]
    for k, t in c["top"].items():
        lines.append(f"| Top-{k} | {t['a']} | {t['b']} | {t['only_a']} | {t['only_b']} | {t['p']:.3f} |")
    ca, cb = c["cost"]["a"], c["cost"]["b"]
    lines += ["", "| Cost per bug (mean) | A | B |", "|---|---:|---:|",
              f"| model calls | {ca['calls']:.0f} | {cb['calls']:.0f} |",
              f"| tokens | {ca['tokens']:,.0f} | {cb['tokens']:,.0f} |",
              f"| wall time (min) | {ca['wall_s'] / 60:.1f} | {cb['wall_s'] / 60:.1f} |", "",
              "| Bug | rank A | rank B | stage A | stage B |", "|---|---:|---:|---|---|"]
    for r in c["rows"]:
        lines.append(f"| {r['bug']} | {r['rank_a'] or '-'} | {r['rank_b'] or '-'} | {r['stage_a']} | {r['stage_b']} |")
    if c["infra"]:
        lines += ["", "Excluded (infrastructure failure): " + ", ".join(f"{n} ({x}/{y})" for n, x, y in c["infra"])]
    lines += ["", "Small samples: a p-value above 0.05 means the difference could be chance, not that there is none."]
    return "\n".join(lines)
