"""Write reports/final/SMOKE_REPORT.md for the smoke runs of csc/smoke_all.sh (run on Roihu after the judge job).

Checks, per run: the job's safeguard line (per-bug limit, stuck-bug guard, circuit breaker) as the runner printed
it; no guard fired by accident; every bug either has a per-bug result file or failed for an EXPECTED reason;
time and billing units per bug; the judge replays asked every pair in both orders.

    python3 scripts/final/smoke_report.py <run> [<run> ...] --logs $FL_ROOT/logs --judge-root $FL_ROOT/judge-vllm
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_order_check import PAIRWISE, check_folder  # noqa: E402

EXPECTED_FAIL = {  # bug -> reasons seen in every earlier pipeline (benchmark or model-answer problems)
    "Closure-115": {"no_failing_test_output"}, "Mockito-1": {"no_failing_test_output"},
    "Gson-14": {"", "no_result"}, "Closure-171": {"other"},
}
GUARD_RE = re.compile(r"timeout (\d+)s, tail guard ([^,]+), circuit breaker ([^)\n]+)")


def last_rows(run_dir):
    rows = {}
    p = os.path.join(run_dir, "runs.jsonl")
    if os.path.exists(p):
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                rows[r["bug"]] = r
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--reports", default="reports")
    ap.add_argument("--logs", required=True)
    ap.add_argument("--judge-root", required=True)
    ap.add_argument("--out", default=os.path.join("reports", "final", "SMOKE_REPORT.md"))
    a = ap.parse_args()
    out = ["# Smoke report", "", "Made by `scripts/final/smoke_report.py`. CHECK = needs a look before the official runs.", ""]
    problems = 0
    out += ["## Front-end runs", "",
            "| Run | bugs | ok | failed (reason) | unexpected failures | guards as received | guard fired | min / BU per bug | code version |",
            "|---|---:|---:|---|---|---|---|---|---|"]
    for run in a.runs:
        d = os.path.join(a.reports, run)
        rows = last_rows(d)
        if not rows:
            out.append(f"| {run} | - | - | - | **CHECK: no runs.jsonl in {d}** | | | | |")
            problems += 1
            continue
        ok = [b for b, r in rows.items() if r["status"] == "ok"]
        no_file = [b for b in ok if not glob.glob(os.path.join(d, "bugs", f"*-{b}", "result.json"))]
        failed = {b: (r.get("error_class") or r["status"]) for b, r in rows.items() if r["status"] != "ok"}
        unexpected = []
        for b, why in failed.items():
            allowed = EXPECTED_FAIL.get(b, set())
            if why not in allowed and rows[b]["status"] not in allowed:
                unexpected.append(f"{b} ({why})")
        unexpected += [f"{b} (ok but no result.json)" for b in no_file]
        logs = sorted(glob.glob(os.path.join(a.logs, f"fl-{run}-*.out")), key=os.path.getmtime)
        text = open(logs[-1], errors="replace").read() if logs else ""
        m = GUARD_RE.search(text)
        guards = f"{m.group(1)} s; {m.group(2)}; {m.group(3).strip()}" if m else "**CHECK: line not found**"
        expected_guards = m and m.group(1) == "3600" and "3 x p95 >= 600s" in m.group(2) and "50%" in m.group(3)
        fired = [x for x in ("tail_timeout", "circuit breaker:") if x in text] + \
                [b for b, r in rows.items() if r.get("error_class") == "tail_timeout"]
        meta = {}
        try:
            meta = json.load(open(os.path.join(d, "job_meta.json")))["jobs"][-1]
        except (OSError, ValueError, KeyError, IndexError):
            pass
        per_bug = (f"{meta['elapsed_s'] / 60 / max(1, len(rows)):.1f} / {meta['gpu_billing_units_est'] / max(1, len(rows)):.1f}"
                   if meta else "**CHECK: no job_meta**")
        problems += bool(unexpected) + (not expected_guards) + bool(fired) + (not meta)
        out.append(f"| {run} | {len(rows)} | {len(ok)} | " + (", ".join(f"{b} ({w})" for b, w in failed.items()) or "-")
                   + f" | {'**CHECK: ' + ', '.join(unexpected) + '**' if unexpected else 'none'} | "
                   + (guards if expected_guards else f"**CHECK: {guards}**")
                   + f" | {'**CHECK: ' + ', '.join(fired) + '**' if fired else 'no'} | {per_bug} | "
                   + f"{meta.get('git_commit', 'not recorded')[:10]}{' (+uncommitted)' if meta.get('git_uncommitted_files') else ''} |")
    out += ["", "## Judge replays (every pair asked in both orders)", "",
            "| Run | Selector | bugs judged | pairs | bugs breaking the rule |", "|---|---|---:|---:|---:|"]
    for run in a.runs:
        for sel in PAIRWISE:
            f = os.path.join(a.judge_root, f"{run}-sel-{sel}")
            if not os.path.isdir(f):
                out.append(f"| {run} | {sel} | **CHECK: replay folder missing** | | |")
                problems += 1
                continue
            _, judged, pairs, bad = check_folder(f, sel)
            problems += bool(bad)
            out.append(f"| {run} | {sel} | {judged} | {pairs} | {len(bad) if not bad else '**CHECK: ' + str(len(bad)) + '**'} |")
    jobs = []
    for p in glob.glob(os.path.join(a.judge_root, "smoke5-*-judge-job.json")):
        for j in json.load(open(p)).get("jobs", []):
            jobs.append((os.path.basename(p), j.get("elapsed_s"), j.get("gpu_billing_units_est"), j.get("call_timeout_s")))
    if jobs:
        out += ["", "Judge job time per run: " + "; ".join(f"{n}: {e} s, {b} BU, question limit {t} s" for n, e, b, t in jobs)]
    out += ["", f"**Items to check: {problems}.** " + ("None: ready to ask the user for the go." if not problems else
                                                         "Look at the CHECK cells before any official run.")]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
