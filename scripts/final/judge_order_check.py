"""A1: prove from the SAVED judge results that every candidate pair was asked in BOTH orders.

Every selector replay folder reports/judge-vllm/<run>-sel-<selector>/bugs/<bug>/result.json has a "selection"
block with: shortlist (the methods compared), pairs (number of pairs), calls + cached_calls (questions sent to the
model, new or answered from the cache). The judge asks each pair twice (A-B and B-A), so for the pairwise selectors
    S5, S8a          calls + cached_calls == 2 * pairs
    S5+S2, S8a+S2    calls + cached_calls == 2 * pairs + (one log-prob question per candidate still tied)  >= 2 * pairs
and pairs == n * (n - 1) / 2 for a shortlist of n methods. A bug breaking either rule is listed.

    python scripts/final/judge_order_check.py [reports/judge-vllm] [--out reports/final/JUDGE_ORDER_CHECK.md]
Read only, except the --out file.
"""
import argparse
import glob
import json
import os
import re

PAIRWISE = {"S5": 0, "S8a": 0, "S5+S2": 1, "S8a+S2": 1}   # 1 = may add log-prob questions on top


def check_folder(folder, selector):
    plus = PAIRWISE[selector]
    n_bugs = judged = pairs_total = 0
    bad = []
    for p in sorted(glob.glob(os.path.join(folder, "bugs", "*", "result.json"))):
        n_bugs += 1
        try:
            sel = json.load(open(p)).get("selection") or {}
        except (OSError, ValueError) as exc:
            bad.append((p.split(os.sep)[-2], f"unreadable: {exc}"))
            continue
        n = len(sel.get("shortlist") or [])
        pairs = sel.get("pairs", 0)
        asked = (sel.get("calls") or 0) + (sel.get("cached_calls") or 0)
        if n < 2 and not pairs:
            continue                                   # nothing to judge (no tie, or no failure context)
        judged += 1
        pairs_total += pairs
        problems = []
        if pairs != n * (n - 1) // 2:
            problems.append(f"pairs {pairs} != {n * (n - 1) // 2} for {n} methods")
        if (asked != 2 * pairs) if not plus else (asked < 2 * pairs):
            problems.append(f"questions {asked} vs pairs {pairs} (expected {'' if not plus else '>= '}{2 * pairs})")
        if problems:
            bad.append((p.split(os.sep)[-2], "; ".join(problems)))
    return n_bugs, judged, pairs_total, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", nargs="?", default=os.path.join("reports", "judge-vllm"))
    ap.add_argument("--out", default=os.path.join("reports", "final", "JUDGE_ORDER_CHECK.md"))
    ap.add_argument("--runs", default="*", help="only replay folders of runs matching this pattern (e.g. '*d4j2new*')")
    a = ap.parse_args()
    rows, all_bad = [], []
    for folder in sorted(glob.glob(os.path.join(a.root, a.runs + "-sel-*"))):
        m = re.match(r"(.+)-sel-(.+)$", os.path.basename(folder))
        if not m or m.group(2) not in PAIRWISE:
            continue
        n_bugs, judged, pairs, bad = check_folder(folder, m.group(2))
        rows.append((m.group(1), m.group(2), n_bugs, judged, pairs, len(bad)))
        all_bad += [(m.group(1), m.group(2), b, why) for b, why in bad]
    lines = ["# Judge order check (A1)", "",
             "Rule: each pair of shortlisted methods must be asked twice, once in each order. Source: the `selection` "
             "block of every per-bug `result.json` in the replay folders (calls + cached calls vs pairs).", "",
             "| Run | Selector | bugs | bugs judged | pairs | bugs breaking the rule |", "|---|---|---:|---:|---:|---:|"]
    lines += [f"| {r} | {s} | {n} | {j} | {p} | {b} |" for r, s, n, j, p, b in rows]
    lines += ["", f"**Total bugs breaking the rule: {len(all_bad)}**" + (" (none: every pair was asked in both orders)"
                                                                         if not all_bad else "")]
    if all_bad:
        lines += ["", "| Run | Selector | Bug | Problem |", "|---|---|---|---|"]
        lines += [f"| {r} | {s} | {b} | {w} |" for r, s, b, w in all_bad]
    if not rows:
        lines += ["", f"No pairwise replay folders found under {a.root}."]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
