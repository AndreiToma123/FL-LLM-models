"""Final-run analysis for the thesis (execution plan of 2026-11-09, items A2-A6 and the 3-run tables).

Read only: it reads reports/<run>/ (front-end runs) and the judge replays (default reports/judge-vllm/) and writes
Markdown/CSV under reports/final/. Run from the repository root.

  python scripts/final/analyze.py perbug  <run> [<run> ...]        A6: per-bug file + Top-1/3/5, MRR, mean rank
  python scripts/final/analyze.py cost    <run> [<run> ...]        A2: model calls (= questions sent) per bug
  python scripts/final/analyze.py recall  <soapfl run> [...]       A4: class recall for k = 1..5
  python scripts/final/analyze.py bookkeeping <run> [<run> ...]    A5: which bugs did not run, and why
  python scripts/final/analyze.py settings <run> [<run> ...]       A3: settings sheet
  python scripts/final/analyze.py tables --dataset d4j14 [--reps 3] 3-run tables (median, range, McNemar)

Common options: --judge-root DIR (default reports/judge-vllm), --selector S8a+S2 (the judge replay used for
"+ judge"), --out DIR (default reports/final).

Counting rules (same as the proposal): every bug of the dataset counts; a bug without output is a miss. A
"model call" is one question sent to the model; a pair judged in both orders is 2 calls.
"""
import argparse
import csv
import glob
import json
import os
import statistics
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from fl_tools.bugs import DATASETS, all_bugs  # noqa: E402

MISS = 10 ** 6
_SPLIT = json.load(open(os.path.join(ROOT, "configs", "selection_split.json")))
DESIGN_BUGS = set(_SPLIT["dev"]) | set(_SPLIT["test"])   # the 100 bugs the judge was designed and first tested on
SETTINGS = [  # (label, run-name pattern; {d} = dataset suffix, {r} = repetition suffix)
    ("SoapFL", "runall-qwen25coder{d}-csc{r}"),
    ("Class widening (always)", "runall-qwen25coder-ca3{d}-csc{r}"),
    ("Class widening (gated)", "runall-qwen25coder-ca3g{d}-csc{r}"),
]
DATASET_SUFFIX = {"d4j14": "", "d4j2new": "-d4j2new", "ghrb": "-ghrb", "gitbug": "-gitbug"}
DATASET_LABEL = {"d4j14": "Defects4J 1.4.0", "d4j2new": "Defects4J 2.0 new bugs", "ghrb": "GHRB",
                 "gitbug": "GitBug-Java"}


# ---------------------------------------------------------------- reading one run
def outer_class(name):
    return name.split("::")[0].split("$")[0]


def _bug_of_dir(d):
    return d.split("-", 1)[1] if d.startswith("d4j") else d


def load_jsonl(path):
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    return rows


def run_meta(run_dir):
    p = os.path.join(run_dir, "run_meta.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def universe(run_dir):
    """All bugs of the run's dataset (misses included); falls back to the bugs the run attempted."""
    ds = run_meta(run_dir).get("dataset") or ("d4j14" if os.path.basename(run_dir).find("d4j2new") < 0 else "d4j2new")
    attempted = {r["bug"] for r in load_jsonl(os.path.join(run_dir, "runs.jsonl"))}
    if ds in DATASETS:
        return [b.name for b in all_bugs(dataset=ds)], ds
    return sorted(attempted), ds


def read_run(run_dir, sel_dir=None):
    """bug -> dict(status, error, rank, class_right, calls, tokens, judge_calls). sel_dir: judge replay folder."""
    bugs, ds = universe(run_dir)
    last = {}
    for r in load_jsonl(os.path.join(run_dir, "runs.jsonl")):
        last[r["bug"]] = r
    per_csv = {}
    p = os.path.join(run_dir, "per_bug.csv")
    if os.path.exists(p):
        for row in csv.DictReader(open(p)):
            per_csv[f"{row['project']}-{row['bug_id']}"] = row
    src = sel_dir or run_dir
    out = {}
    for d in glob.glob(os.path.join(run_dir, "bugs", "*")):
        name = _bug_of_dir(os.path.basename(d))
        truth_p, res_p = os.path.join(d, "ground_truth.json"), os.path.join(src, "bugs", os.path.basename(d), "result.json")
        truth = set(json.load(open(truth_p)).get("buggy_methods") or []) if os.path.exists(truth_p) else set()
        rec = {"truth": truth}
        if os.path.exists(res_p):
            res = json.load(open(res_p))
            names = [m["method_name"] if isinstance(m, dict) else m for m in res.get("buggy_methods") or []]
            rec["rank"] = next((i + 1 for i, n in enumerate(names) if n in truth), MISS) if truth else MISS
            rec["has_output"] = True
            # SoapFL's own rule (Evaluation/evaluate.py, ported in fl_tools/score.py): a ranked method lies in a
            # class of a real buggy method
            truth_cls = {outer_class(m) for m in truth}
            rec["class_right"] = any((m.get("class_name") if isinstance(m, dict) else outer_class(m)) in truth_cls
                                     for m in res.get("buggy_methods") or [])
            sel = res.get("selection") or {}
            rec["judge_calls"] = (sel.get("calls") or 0) + (sel.get("cached_calls") or 0) if sel_dir else 0
        out[name] = rec
    table = {}
    for b in bugs:
        rec = out.get(b, {})
        r = last.get(b, {})
        c = per_csv.get(b, {})
        table[b] = {
            "status": r.get("status", "not run"), "error": r.get("error_class", ""),
            "has_output": rec.get("has_output", False), "rank": rec.get("rank", MISS),
            "class_right": rec.get("class_right", False),
            "calls": int(c.get("llm_calls") or 0) if c.get("llm_calls") not in (None, "", "N/A") else 0,
            "tokens": int(c.get("total_tokens") or 0) if c.get("total_tokens") not in (None, "", "N/A") else 0,
            "judge_calls": rec.get("judge_calls", 0),
        }
    return table, ds


def metrics(table):
    ranks = [v["rank"] for v in table.values()]
    n = len(ranks)
    found = [r for r in ranks if r < MISS]
    with_out = [v for v in table.values() if v["has_output"]]
    return {
        "bugs": n, "with_output": len(with_out), "no_output": n - len(with_out),
        "top1": sum(r <= 1 for r in ranks), "top3": sum(r <= 3 for r in ranks), "top5": sum(r <= 5 for r in ranks),
        "found": len(found), "mrr": round(sum(1 / r for r in found) / n, 3) if n else 0.0,
        "mean_rank_found": round(statistics.mean(found), 2) if found else None,
        "class_right": sum(v["class_right"] for v in table.values()),
        "calls_per_bug": round(statistics.mean([v["calls"] for v in with_out]), 1) if with_out else 0.0,
        "tokens_per_bug": round(statistics.mean([v["tokens"] for v in with_out])) if with_out else 0,
        "judge_calls_per_bug": round(sum(v["judge_calls"] for v in table.values()) / n, 1) if n else 0.0,
    }


def mcnemar(a, b, n_top=1):
    """Exact two-sided McNemar on the shared bug universe: (gained by b, lost by b, p)."""
    bugs = set(a) | set(b)
    g = lambda t, x: t.get(x, {}).get("rank", MISS)
    gain = sum(g(b, x) <= n_top < g(a, x) for x in bugs)
    loss = sum(g(a, x) <= n_top < g(b, x) for x in bugs)
    m, k = gain + loss, min(gain, loss)
    p = 1.0 if m == 0 else min(1.0, 2 * sum(comb(m, i) for i in range(k + 1)) / 2 ** m)
    return gain, loss, p


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, running = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = running
    return adj


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    print(f"wrote {path}")


def _sel_dir(args, run):
    d = os.path.join(args.judge_root, f"{run}-sel-{args.selector}")
    return d if os.path.isdir(d) else None


# ---------------------------------------------------------------- commands
def cmd_perbug(args):
    lines = ["# Per-bug results (A6)", "", "Every bug of the dataset counts; no output = not found. MRR = average of "
             "1/rank over all bugs (not found = 0). Mean rank = over the bugs whose buggy method is in the list.", "",
             "| Run | bugs | with output | Top-1 | Top-3 | Top-5 | found | MRR | mean rank (found) | right class |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for run in args.runs:
        run_dir = os.path.join(args.reports, run)
        for label, sel in ((run, None), (f"{run} + {args.selector}", _sel_dir(args, run))):
            if label != run and not sel:
                continue
            table, _ = read_run(run_dir, sel)
            name = run if not sel else f"{run}+{args.selector}"
            rows = ["bug,status,error,has_output,rank,class_right,model_calls,tokens,judge_calls"]
            for b, v in sorted(table.items()):
                rows.append(",".join(str(x) for x in (b, v["status"], v["error"], v["has_output"],
                                                       v["rank"] if v["rank"] < MISS else "not found",
                                                       v["class_right"], v["calls"], v["tokens"], v["judge_calls"])))
            _write(os.path.join(args.out, "perbug", f"{name}.csv"), "\n".join(rows) + "\n")
            m = metrics(table)
            lines.append(f"| {label} | {m['bugs']} | {m['with_output']} | {m['top1']} | {m['top3']} | {m['top5']} | "
                         f"{m['found']} | {m['mrr']} | {m['mean_rank_found']} | {m['class_right']} |")
    _write(os.path.join(args.out, "PER_BUG_SUMMARY.md"), "\n".join(lines) + "\n")


def cmd_cost(args):
    lines = ["# Cost per bug (A2)", "",
             "**One model call = one question sent to the model.** A pair of methods judged in both orders = 2 calls; "
             "a log-probability score question = 1 call. Front-end calls are averaged over the bugs with output "
             "(`per_bug.csv`, column `llm_calls`); judge calls over all bugs of the dataset (bugs the judge does not "
             "need to look at count as 0), and include answers taken from the cache, because a fresh run would ask them.",
             "", f"| Run | front-end calls / bug | tokens / bug | judge calls / bug ({args.selector}) | total calls / bug |",
             "|---|---:|---:|---:|---:|"]
    for run in args.runs:
        run_dir = os.path.join(args.reports, run)
        fe = metrics(read_run(run_dir)[0])
        sel = _sel_dir(args, run)
        jc = metrics(read_run(run_dir, sel)[0])["judge_calls_per_bug"] if sel else None
        tot = round(fe["calls_per_bug"] + (jc or 0), 1)
        lines.append(f"| {run} | {fe['calls_per_bug']} | {fe['tokens_per_bug']:,} | "
                     f"{jc if jc is not None else 'no replay found'} | {tot} |")
    _write(os.path.join(args.out, "COST.md"), "\n".join(lines) + "\n")


def cmd_recall(args):
    from fl_tools.classaug import rank_classes
    ctx_dir = os.path.join(args.reports, "_failure_context")
    lines = ["# Class recall for k = 1..5 (A4)", "",
             "Bugs with output, a failure-context file and a known answer. 'Free ranking top-k' = the class ranking "
             "used by class widening (stack position, name overlap, coverage; fixed key). 'SoapFL + top-k' = SoapFL's "
             "own class plus the free ranking's top k (what class widening 'always' tries; the real pipeline can only "
             "add classes SoapFL offered to its model, so it can be a little lower). k = 3 was fixed after an offline "
             "study on dataset 1 AND dataset 2 class results (roadmap 3l), so neither dataset is a clean test of k.", ""]
    for run in args.runs:
        run_dir = os.path.join(args.reports, run)
        n, soap = 0, 0
        free = [0] * 6
        plus = [0] * 6
        for d in sorted(glob.glob(os.path.join(run_dir, "bugs", "*"))):
            dn = os.path.basename(d)
            tp, rp, cp = (os.path.join(d, "ground_truth.json"), os.path.join(d, "result.json"),
                          os.path.join(ctx_dir, dn + ".json"))
            if not (os.path.exists(tp) and os.path.exists(rp) and os.path.exists(cp)):
                continue
            truth = {outer_class(m) for m in json.load(open(tp)).get("buggy_methods") or []}
            if not truth:
                continue
            chosen = {outer_class(c) for c in json.load(open(rp)).get("buggy_classes") or []}
            ranking = rank_classes(json.load(open(cp)))
            n += 1
            soap += bool(chosen & truth)
            for k in range(1, 6):
                free[k] += bool(set(ranking[:k]) & truth)
                plus[k] += bool((chosen | set(ranking[:k])) & truth)
        pct = lambda x: f"{x} ({100 * x / n:.0f}%)" if n else "-"
        lines += [f"## {run} ({n} bugs)", "", f"SoapFL's own class: {pct(soap)}", "",
                  "| k | free ranking top-k | SoapFL + free top-k |", "|---:|---:|---:|"]
        lines += [f"| {k} | {pct(free[k])} | {pct(plus[k])} |" for k in range(1, 6)] + [""]
    _write(os.path.join(args.out, "CLASS_RECALL_K.md"), "\n".join(lines) + "\n")


def cmd_bookkeeping(args):
    lines = ["# Bug bookkeeping (A5)", ""]
    d1 = DATASETS["d4j14"]["table"]
    dep = [f"{p}-{i}" for p, s in d1.items() for i in s["deprecate"]]
    lines += [f"**395 vs 388 (dataset 1):** SoapFL's own `run_all.py` skips {len(dep)} bug ids, so the batch has 388 "
              f"bugs while the paper's Table I lists 395: {', '.join(dep)} (`fl_tools/bugs.py`, `deprecate`). "
              "Defects4J marks these ids deprecated. They are not run in any of our pipelines.", ""]
    for run in args.runs:
        run_dir = os.path.join(args.reports, run)
        table, ds = read_run(run_dir)
        rows = load_jsonl(os.path.join(run_dir, "runs.jsonl"))
        attempts = {}
        for r in rows:
            attempts.setdefault(r["bug"], []).append(r)
        bad = {b: v for b, v in table.items() if not v["has_output"]}
        by = {}
        for b, v in bad.items():
            by.setdefault(f"{v['status']} / {v['error'] or '-'}", []).append(b)
        lines += [f"## {run}", "", f"{len(table)} bugs, {len(table) - len(bad)} with output, {len(bad)} without:", "",
                  "| status / reason | bugs | which |", "|---|---:|---|"]
        lines += [f"| {k} | {len(v)} | {', '.join(sorted(v))} |" for k, v in sorted(by.items(), key=lambda x: -len(x[1]))]
        multi = {b: a for b, a in attempts.items() if len(a) > 1}
        if multi:
            lines += ["", f"Bugs with more than one attempt in runs.jsonl ({len(multi)}): "
                      + "; ".join(f"{b}: " + " -> ".join(f"{x['status']}{'/' + x['error_class'] if x.get('error_class') else ''}"
                                                     for x in a) for b, a in sorted(multi.items()))]
        mock = [b for b in bad if b.startswith("Mockito-")]
        if mock:
            lines += ["", f"Mockito without output: {len(mock)} ("
                      + ", ".join(f"{k}: {sum(1 for b in mock if bad[b]['status'] + ' / ' + (bad[b]['error'] or '-') == k)}"
                                  for k in sorted({bad[b]['status'] + ' / ' + (bad[b]['error'] or '-') for b in mock})) + ")"]
        lines.append("")
    _write(os.path.join(args.out, "BUG_BOOKKEEPING.md"), "\n".join(lines) + "\n")


def cmd_settings(args):
    models = json.load(open(os.path.join(ROOT, "configs", "models.json")))
    lines = ["# Settings sheet (A3)", "",
             "| Run | model (checkpoint) | weights id | served by | context / max answer | sampling | seed | "
             "code version | patch digest | prompts |", "|---|---|---|---|---|---|---|---|---|---|"]
    for run in args.runs:
        run_dir = os.path.join(args.reports, run)
        meta = run_meta(run_dir)
        jm = {}
        p = os.path.join(run_dir, "job_meta.json")
        if os.path.exists(p):
            jobs = json.load(open(p)).get("jobs") or []
            jm = jobs[-1] if jobs else {}
        env = meta.get("llm_env", {})
        prompts = {"soapfl": "SoapFL's own (patched SoapFL checkout, CompanyConfig/Default)",
                   "classaug": "SoapFL's own; class list from fl_tools/classaug.py (digest "
                               + str(meta.get("classaug_digest", "?")) + ")",
                   "hypodeduce": "fl_tools/hypodeduce/config"}.get(meta.get("pipeline", "soapfl"), "?")
        lines.append(
            f"| {run} | {jm.get('model', '?')} (instruct, bf16, not quantized) | {jm.get('model_weights_id', 'not recorded')} | "
            f"{jm.get('vllm_module', '?')} | {env.get('SOAPFL_CONTEXT_LIMIT', jm.get('context', '?'))} / "
            f"{env.get('SOAPFL_MAX_COMPLETION_TOKENS', jm.get('max_completion_tokens', '?'))} | temperature 0 (greedy; SoapFL/camel default) | "
            f"SoapFL {meta.get('seed', '?')}, vLLM 0 | {jm.get('git_commit', 'not recorded')} | {meta.get('patch_digest', '?')} | {prompts} |")
    lines += ["", "Judge: same model and server, temperature 0, answers of 1-2 tokens, prompts in "
              "`fl_tools/selection/prompts.py` (hash stored as `prompt_version` in each `<run>-selection.json`). "
              "SoapFL commit: " + ", ".join(sorted({run_meta(os.path.join(args.reports, r)).get('soapfl_commit', '?')[:10]
                                                    for r in args.runs})) + "."]
    lines += ["", "Presets: " + "; ".join(f"{k} = {v.get('hf')}" for k, v in models.items() if not k.startswith("_") and v.get("hf"))]
    _write(os.path.join(args.out, "SETTINGS.md"), "\n".join(lines) + "\n")


def cmd_tables(args):
    ds, reps = args.dataset, args.reps
    dsuf = DATASET_SUFFIX.get(ds, f"-{ds}")
    rsufs = [f"-r{i}" for i in range(1, reps + 1)] if reps > 0 else [""]
    data = {}   # (label, judged) -> list of tables per rep (None if missing)
    for label, pat in SETTINGS:
        for judged in (False, True):
            tabs = []
            for rs in rsufs:
                run = pat.format(d=dsuf, r=rs)
                run_dir = os.path.join(args.reports, run)
                if not os.path.isdir(run_dir):
                    tabs.append(None)
                    continue
                sel = _sel_dir(args, run) if judged else None
                t = read_run(run_dir, sel)[0] if (sel or not judged) else None
                if t is not None and args.heldout:
                    t = {b: v for b, v in t.items() if b not in DESIGN_BUGS}
                tabs.append(t)
            data[(label, judged)] = tabs
    n_held = next((len(t) for ts in data.values() for t in ts if t), 0)
    part = (f" - only the {n_held} bugs never used to design the "
            "judge (the 100-bug design sample of configs/selection_split.json left out)") if args.heldout else ""
    lines = [f"# {DATASET_LABEL.get(ds, ds)}{part}: results over {len(rsufs)} run(s)", "",
             f"Judge = selector {args.selector} replayed on each run's own candidate lists. Every bug counts; a bug "
             "without output is a miss. Median and range (min-max) over the runs that exist.", ""]
    for top, key in ((1, "top1"), (3, "top3"), (5, "top5")):
        lines += [f"## Top-{top}", "", "| Pipeline | " + " | ".join(f"run {i + 1}" for i in range(len(rsufs)))
                  + " | median | range |", "|---|" + "---:|" * (len(rsufs) + 2)]
        for (label, judged), tabs in data.items():
            vals = [metrics(t)[key] if t else None for t in tabs]
            have = [v for v in vals if v is not None]
            med = statistics.median(have) if have else None
            lines.append(f"| {label}{' + judge' if judged else ''} | " + " | ".join("-" if v is None else str(v) for v in vals)
                         + f" | {'-' if med is None else med} | {f'{min(have)}-{max(have)}' if have else '-'} |")
        lines.append("")
    # cost and bugs under the table
    lines += ["## Bugs and cost", "", "| Pipeline | bugs | without output (per run) | front-end calls / bug (bugs with output) | tokens / bug (bugs with output) | judge calls / bug (all bugs) |",
              "|---|---:|---|---:|---:|---:|"]
    for (label, judged), tabs in data.items():
        have = [metrics(t) for t in tabs if t]
        if not have:
            continue
        lines.append(f"| {label}{' + judge' if judged else ''} | {have[0]['bugs']} | "
                     + ", ".join(str(m["no_output"]) for m in have)
                     + f" | {statistics.median(m['calls_per_bug'] for m in have)} | {statistics.median(m['tokens_per_bug'] for m in have):,} | "
                     + f"{statistics.median(m['judge_calls_per_bug'] for m in have) if judged else '-'} |")
    # significance: median run of each pipeline vs the median run of plain SoapFL
    def median_run(tabs):
        have = [(metrics(t)["top1"], i, t) for i, t in enumerate(tabs) if t]
        if not have:
            return None, None
        have.sort(key=lambda x: (x[0], x[1]))
        return have[(len(have) - 1) // 2][2], have[(len(have) - 1) // 2][1]
    base, _ = median_run(data[("SoapFL", False)])
    main = {("Class widening (always)", False): "RQ1", ("Class widening (gated)", False): "RQ2", ("SoapFL", True): "RQ3"}
    comps = []
    for key, tabs in data.items():
        if key == ("SoapFL", False) or base is None:
            continue
        t, idx = median_run(tabs)
        if t is None:
            continue
        g, l, p = mcnemar(base, t)
        same = sum(1 for i, x in enumerate(tabs) if x and data[("SoapFL", False)][i]
                   and mcnemar(data[("SoapFL", False)][i], x)[0] > mcnemar(data[("SoapFL", False)][i], x)[1])
        n_pairs = sum(1 for i, x in enumerate(tabs) if x and data[("SoapFL", False)][i])
        comps.append((key, idx, g, l, p, same, n_pairs))
    expl = [c for c in comps if c[0] not in main]
    adj = dict(zip([c[0] for c in expl], holm([c[4] for c in expl])))
    lines += ["", "## Paired test against plain SoapFL (Top-1, exact McNemar on the median run of each pipeline)", "",
              "One main comparison per research question (RQ1, RQ2, RQ3; this choice of main comparisons is Claude's "
              "proposal of 2026-11-09 and must be confirmed by the user before the official runs); the others are "
              "exploratory and their p-values "
              "are Holm-corrected. 'Runs with a gain' = in how many run pairs (run i vs run i of SoapFL) the pipeline "
              "gained more bugs than it lost.", "",
              "| Pipeline vs SoapFL | role | median run used | gained / lost | p | p (Holm) | runs with a gain |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for key, idx, g, l, p, same, n_pairs in comps:
        lines.append(f"| {key[0]}{' + judge' if key[1] else ''} | {main.get(key, 'exploratory')} | {idx + 1} | "
                     f"+{g} / -{l} | {p:.3g} | {'-' if key in main else f'{adj[key]:.3g}'} | {same} of {n_pairs} |")
    # run-to-run stability
    lines += ["", "## How many bugs change between runs (Top-1 hit or not)", "", "| Pipeline | run pair | bugs that flip |",
              "|---|---|---:|"]
    for (label, judged), tabs in data.items():
        for i in range(len(tabs)):
            for j in range(i + 1, len(tabs)):
                if tabs[i] and tabs[j]:
                    flips = sum((tabs[i][b]["rank"] <= 1) != (tabs[j].get(b, {}).get("rank", MISS) <= 1) for b in tabs[i])
                    lines.append(f"| {label}{' + judge' if judged else ''} | {i + 1} vs {j + 1} | {flips} |")
    _write(os.path.join(args.out, f"TABLES_{ds}{'_heldout' if args.heldout else ''}.md"), "\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["perbug", "cost", "recall", "bookkeeping", "settings", "tables"])
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--reports", default="reports")
    ap.add_argument("--judge-root", default=os.path.join("reports", "judge-vllm"))
    ap.add_argument("--selector", default="S8a+S2")
    ap.add_argument("--out", default=os.path.join("reports", "final"))
    ap.add_argument("--dataset", default="d4j14")
    ap.add_argument("--heldout", action="store_true",
                    help="tables: only the bugs outside the 100-bug design sample (288 on dataset 1)")
    ap.add_argument("--reps", type=int, default=1, help="tables: runs per setting (-r1..-rN; default 1 = the -r1 runs); 0 = the old unsuffixed runs")
    args = ap.parse_args(argv)
    if args.command != "tables" and not args.runs:
        ap.error("give at least one run name (folder under --reports)")
    globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    main()
