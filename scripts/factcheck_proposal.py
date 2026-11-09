"""Recompute every number of the Master Thesis Proposal from the result files (read only, writes nothing).

Run from the repository root:   python scripts/factcheck_proposal.py
Needs: reports/<run>/ for the 8 full CSC runs (in git) and reports/judge-vllm/ (NOT in git; the HypoDeduce
judge files come from judge-hd.tgz). Missing folders are reported and skipped.

Counting rule (same as the proposal): every bug of the dataset counts; a bug without output is a miss.
Paired test: exact two-sided McNemar test (binomial test on the bugs where exactly one of the two pipelines is right).
"""
import csv
import glob
import json
import os
from math import comb, sqrt

R = "reports"
J = os.path.join(R, "judge-vllm")
RUNS = {  # short name -> (dataset, folder)
    "SoapFL": "runall-qwen25coder{d}-csc",
    "always": "runall-qwen25coder-ca3{d}-csc",
    "gated": "runall-qwen25coder-ca3g{d}-csc",
    "HypoDeduce": "runall-qwen25coder-hd-h5c5m3{d}-csc",
}
DATASETS = {"dataset 1 (388 bugs)": "", "dataset 2 (444 bugs)": "-d4j2new"}


def mcnemar(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def wilson(k, n, z=1.96):
    p = k / n
    centre, half = p + z * z / (2 * n), z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * (centre - half) / (1 + z * z / n), 100 * (centre + half) / (1 + z * z / n)


def truth(run):
    out = {}
    for p in glob.glob(os.path.join(R, run, "bugs", "*", "ground_truth.json")):
        out[p.split(os.sep)[-2]] = set(json.load(open(p)).get("buggy_methods") or [])
    return out


def ranks(folder, run):
    """bug -> rank of the first real buggy method (999 = not in the list); bugs without output are absent."""
    out = {}
    for bug, t in truth(run).items():
        p = os.path.join(folder, "bugs", bug, "result.json")
        if t and os.path.exists(p):
            names = [m["method_name"] if isinstance(m, dict) else m
                     for m in json.load(open(p)).get("buggy_methods") or []]
            out[bug] = next((i + 1 for i, n in enumerate(names) if n in t), 999)
    return out


def compare(label, a, b):
    bugs, g = set(a) | set(b), lambda d, x: d.get(x, 999)
    parts = []
    for n, name in ((1, "Top-1"), (3, "Top-3"), (5, "Top-5"), (998, "reaches list")):
        A = sum(g(a, x) <= n for x in bugs)
        B = sum(g(b, x) <= n for x in bugs)
        gain = sum(g(b, x) <= n < g(a, x) for x in bugs)
        loss = sum(g(a, x) <= n < g(b, x) for x in bugs)
        parts.append(f"{name} {A} vs {B} (+{gain}/-{loss}, p={mcnemar(gain, loss):.3f})")
    print(f"  {label}: " + "; ".join(parts))


def summary_row(run):
    path = os.path.join(R, run, "summary.md")
    for line in open(path) if os.path.exists(path) else []:
        if line.startswith("| ALL"):
            return line.strip()
    return "summary.md missing"


def per_bug_means(run):
    rows = [x for x in csv.DictReader(open(os.path.join(R, run, "per_bug.csv"))) if x["has_result"] == "True"]
    return sum(int(x["llm_calls"] or 0) for x in rows) / len(rows)


def billing(run):
    try:
        return [(j["slurm_job_id"], j["elapsed_s"] // 60, j["gpu_billing_units_est"])
                for j in json.load(open(os.path.join(R, run, "job_meta.json")))["jobs"]]
    except OSError:
        return "no job_meta.json"


if __name__ == "__main__":
    for ds, d in DATASETS.items():
        print(f"\n================ {ds}")
        rk = {}
        for name, pat in RUNS.items():
            run = pat.format(d=d)
            if not os.path.isdir(os.path.join(R, run)):
                print(f"  {name}: folder reports/{run} missing")
                continue
            print(f"\n  {name} ({run})")
            print(f"    summary   {summary_row(run)}")
            print(f"    model calls per bug (bugs with output) {per_bug_means(run):.1f}; jobs {billing(run)}")
            rk[name] = ranks(os.path.join(R, run), run)
            sel = os.path.join(J, f"{run}-sel-S8a+S2")
            if os.path.isdir(sel):
                rk[name + "+judge"] = ranks(sel, run)
            else:
                print(f"    judge folder {sel} missing")
            s5 = os.path.join(J, f"{run}-sel-S5")
            if name == "HypoDeduce" and os.path.isdir(s5):
                rk["HypoDeduce+S5"] = ranks(s5, run)
        n = 388 if d == "" else 444
        if "SoapFL" in rk:
            top1 = sum(v == 1 for v in rk["SoapFL"].values())
            lo, hi = wilson(top1, n)
            print(f"\n  SoapFL Top-1 {top1}/{n} = {100 * top1 / n:.1f}% (95% range {lo:.1f}-{hi:.1f})")
        print("\n  Paired tests (first = A, second = B; +gained/-lost by B):")
        for a, b in (("SoapFL", "always"), ("SoapFL", "gated"), ("SoapFL", "SoapFL+judge"),
                     ("SoapFL", "always+judge"), ("SoapFL+judge", "always+judge"), ("SoapFL+judge", "gated+judge"),
                     ("SoapFL", "HypoDeduce"), ("always", "HypoDeduce"), ("HypoDeduce", "HypoDeduce+judge"),
                     ("HypoDeduce", "HypoDeduce+S5"), ("SoapFL+judge", "HypoDeduce+judge"),
                     ("always+judge", "HypoDeduce+judge")):
            if a in rk and b in rk:
                compare(f"{a} vs {b}", rk[a], rk[b])
            else:
                print(f"  {a} vs {b}: data missing")
        if d == "" and "SoapFL" in rk and "SoapFL+judge" in rk:
            split = json.load(open(os.path.join("configs", "selection_split.json")))
            design = set(split["dev"]) | set(split["test"])
            held = lambda r: {k: v for k, v in r.items() if k.split("-", 1)[1] not in design}
            print("\n  288 bugs never used for design:")
            compare("SoapFL vs SoapFL+judge", held(rk["SoapFL"]), held(rk["SoapFL+judge"]))
