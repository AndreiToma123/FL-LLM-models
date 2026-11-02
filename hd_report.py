"""Summary of the HypoDeduce runs + judge replays, run on Roihu (prints text only, writes nothing)."""
import collections, csv, glob, json, os, sys
from math import comb

REP = os.environ.get("REP", "/projappl/project_2021789/FL-LLM-models/reports")
BK = os.path.expanduser(os.environ.get("BK", "~/roihu-reports-backup"))
J = os.environ.get("J", "/scratch/project_2021789/andreist/fl/judge-vllm")
LOGS = os.environ.get("LOGS", "/scratch/project_2021789/andreist/fl/logs")
EXPECTED = {"no_failing_test_output"}


def find(run):
    for base in (REP, BK):
        if os.path.isfile(os.path.join(base, run, "runs.jsonl")):
            return os.path.join(base, run)
    hits = sorted(glob.glob(os.path.join(BK, run + "*", "runs.jsonl")), key=os.path.getmtime)
    return os.path.dirname(hits[-1]) if hits else None


def truth(src):
    out = {}
    for p in glob.glob(os.path.join(src, "bugs", "*", "ground_truth.json")):
        out[p.split(os.sep)[-2]] = set(json.load(open(p)).get("buggy_methods") or [])
    return out


def ranks_sel(sel, src):
    """bug dir -> rank of the first buggy method (999 = not in the list); only bugs with output."""
    out = {}
    for d, t in truth(src).items():
        p = os.path.join(sel, "bugs", d, "result.json")
        if not os.path.exists(p) or not t:
            continue
        names = [m["method_name"] if isinstance(m, dict) else m for m in json.load(open(p)).get("buggy_methods") or []]
        out[d] = next((i + 1 for i, n in enumerate(names) if n in t), 999)
    return out


def mcn(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def compare(label, a, b):
    com = [x for x in a if x in b]
    if not com:
        print(f"  {label}: no common bugs"); return
    parts = []
    for n, name in ((1, "Top-1"), (3, "Top-3"), (5, "Top-5"), (998, "reach")):
        A = sum(a[x] <= n for x in com); B = sum(b[x] <= n for x in com)
        oa = sum(a[x] <= n < b[x] for x in com); ob = sum(b[x] <= n < a[x] for x in com)
        parts.append(f"{name} {A} vs {B} (+{ob}/-{oa}, p={mcn(oa, ob):.3f})")
    print(f"  {label} [n={len(com)}]: " + "; ".join(parts))


def run_report(run):
    d = find(run)
    print(f"\n===== {run}: {d or 'NOT FOUND'}")
    if not d:
        return
    for line in open(os.path.join(d, "summary.md")) if os.path.exists(os.path.join(d, "summary.md")) else []:
        if line.startswith("| ") and not line.startswith("| Project"):
            print("  " + line.rstrip())
    rows = [json.loads(l) for l in open(os.path.join(d, "runs.jsonl")) if l.strip()]
    last = {r["bug"]: r for r in rows}
    print("  last status:", dict(collections.Counter((r["status"], r.get("error_class", "")) for r in last.values())))
    for b, r in sorted(last.items()):
        if r["status"] != "ok" and r.get("error_class") not in EXPECTED:
            print(f"    {b}: {r['status']} {r.get('error_class', '')} {r.get('wall_s')}s {r.get('error_line', '')[:80]}")
    try:
        for j in json.load(open(os.path.join(d, "job_meta.json")))["jobs"]:
            print(f"  job {j['slurm_job_id']}: {j['elapsed_s'] // 60} min, {j['gpu_billing_units_est']} BU, exit {j['runner_exit']}")
    except Exception as exc:
        print("  job_meta:", exc)
    for f in sorted(glob.glob(os.path.join(LOGS, f"fl-{run}-*.out")))[-2:]:
        for line in open(f, errors="replace"):
            if "bugs selected" in line or "circuit breaker" in line:
                print(f"  {os.path.basename(f)}: {line.strip()[:220]}")
    for name in ("ties.md", "funnel.md"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            for line in open(p):
                if line.startswith(("| actual", "| best", "| random (", "| right class", "| buggy method")):
                    print("  " + line.rstrip())


def judge_report(run):
    p = os.path.join(J, f"{run}-selection.md")
    print(f"\n----- judge on {run}: " + ("" if os.path.exists(p) else "not found"))
    if os.path.exists(p):
        for line in open(p):
            if line.startswith(("### ", "| source", "| random", "| oracle", "| S")):
                print("  " + line.rstrip()[:200])
    g = os.path.join(J, f"{run}-gate.md")
    if os.path.exists(g):
        for line in open(g):
            if line.startswith("| S0"):
                print("  gate " + line.rstrip())


def ranks_run(run, judged=False):
    src = find(run)
    if not src:
        return None
    if judged:
        sel = os.path.join(J, f"{run}-sel-S8a+S2")
        return ranks_sel(sel, src) if os.path.isdir(sel) else None
    return ranks_sel(src, src)


if __name__ == "__main__":
    for sfx, ds in (("", "dataset 1"), ("-d4j2new", "dataset 2")):
        hd = f"runall-qwen25coder-hd-h5c5m3{sfx}-csc"
        run_report(hd)
        judge_report(hd)
        soap, ca = f"runall-qwen25coder{sfx}-csc", f"runall-qwen25coder-ca3{sfx}-csc"
        R = {k: ranks_run(r, j) for k, r, j in (("soap", soap, False), ("ca", ca, False), ("hd", hd, False),
                                                  ("soap+J", soap, True), ("ca+J", ca, True), ("hd+J", hd, True))}
        print(f"\n----- paired comparisons, {ds} (A vs B; +gained/-lost by B)")
        for a, b in (("soap", "hd"), ("ca", "hd"), ("hd", "hd+J"), ("soap+J", "hd+J"), ("ca+J", "hd+J"),
                     ("soap", "ca+J")):
            if R[a] is None or R[b] is None:
                print(f"  {a} vs {b}: missing ({'A' if R[a] is None else 'B'})"); continue
            compare(f"{a} vs {b}", R[a], R[b])
