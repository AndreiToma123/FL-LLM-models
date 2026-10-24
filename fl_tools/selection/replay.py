"""Replay selectors on a finished run and write each result as a run folder of its own."""
import json
import os
import shutil
from typing import Dict, List, Optional

from ..compare import mcnemar_exact
from . import metrics, selectors
from .candidates import BugCase, load_cases
from .split import DEFAULT_SPLIT, load_split, part_of

TOP_FILES_TO_COPY = ("runs.jsonl",)


def _subset(cases: List[BugCase], split: Optional[dict], part: str) -> List[BugCase]:
    if part == "all" or split is None:
        return cases
    return [c for c in cases if part_of(c.bug, split) == part]


def _paired(cases, orders_a, orders_b, k=1):
    only_a = only_b = 0
    for c in cases:
        ra = metrics.first_rank(orders_a.get(c.bug, []), c.truth)
        rb = metrics.first_rank(orders_b.get(c.bug, []), c.truth)
        ha, hb = ra is not None and ra <= k, rb is not None and rb <= k
        only_a += ha and not hb
        only_b += hb and not ha
    return {"only_source": only_a, "only_selector": only_b, "p": mcnemar_exact(only_a, only_b)}


def write_run(src_run: str, dest: str, cases: List[BugCase], orders: Dict[str, List[dict]],
              infos: Dict[str, dict], selector: selectors.Selector, seed: int) -> None:
    """Same layout as an exported run (bugs/<dir>/...), so score/funnel/ties/compare read it unchanged."""
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for name in TOP_FILES_TO_COPY:
        if os.path.exists(os.path.join(src_run, name)):
            shutil.copy2(os.path.join(src_run, name), os.path.join(dest, name))
    meta_path = os.path.join(src_run, "run_meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    meta["selection"] = {"source_run": os.path.basename(os.path.normpath(src_run)), "selector": selector.name,
                         "description": selector.description, "seed": seed, "model_calls": selector.model_calls}
    with open(os.path.join(dest, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    for case in cases:
        rec = case.record
        if rec is None or rec.dir is None:
            continue
        out = os.path.join(dest, "bugs", os.path.basename(rec.dir.rstrip(os.sep)))
        os.makedirs(out, exist_ok=True)
        for name in ("ground_truth.json", "events.jsonl"):
            if os.path.exists(os.path.join(rec.dir, name)):
                shutil.copy2(os.path.join(rec.dir, name), os.path.join(out, name))
        if rec.result is not None:
            result = dict(rec.result)
            result["buggy_methods"] = orders[case.bug]
            result["selection"] = {"selector": selector.name, "seed": seed, **infos.get(case.bug, {})}
            with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)


def replay(run_dir: str, selector_names: List[str], seed: int = 0, draws: int = 2000,
           split_path: Optional[str] = DEFAULT_SPLIT, out_root: Optional[str] = None, write: bool = True,
           soapfl_dir: Optional[str] = None, reveal_test: bool = False) -> dict:
    """reveal_test=False reports only the dev part of the split: choose selectors and settings on dev, then
    run once with reveal_test=True. Without a split (e.g. HypoDeduce lists, test-only) everything is shown."""
    cases = load_cases(run_dir, soapfl_dir)
    split = load_split(split_path) if split_path and os.path.exists(split_path) else None
    run_name = os.path.basename(os.path.normpath(run_dir))
    out_root = out_root or os.path.dirname(os.path.normpath(run_dir))
    source_orders = {c.bug: list(c.candidates) for c in cases if c.candidates}
    parts = (["dev", "test", "all"] if reveal_test else ["dev"]) if split else ["all"]
    report = {"run": run_name, "n_bugs": len(cases), "seed": seed, "parts": {}, "selectors": {}, "written": [],
              "test_hidden": bool(split) and not reveal_test}
    for part in parts:
        sub = _subset(cases, split, part)
        report["parts"][part] = {
            "n": len(sub), "infra_failures": sum(c.infra_failure for c in sub),
            "reachable": sum(c.reachable for c in sub),
            "source": metrics.evaluate(sub, source_orders),
            "random_ties": metrics.random_ties(sub, draws, seed),
            "oracle": metrics.oracle(sub),
        }
    for name in selector_names:
        sel = selectors.get(name)
        orders, infos = {}, {}
        for c in cases:
            if c.candidates:
                orders[c.bug], infos[c.bug] = sel.order(c, seed)
        entry = {"description": sel.description, "parts": {}}
        for part in parts:
            sub = _subset(cases, split, part)
            m = metrics.evaluate(sub, orders)
            ref = report["parts"][part]
            rnd, orc = ref["random_ties"]["top1"]["mean"], ref["oracle"]["top1"]
            m["gain_vs_source"] = m["top1"] - ref["source"]["top1"]
            m["gain_vs_random"] = round(m["top1"] - rnd, 2)
            m["oracle_gap_recovered"] = round((m["top1"] - rnd) / (orc - rnd), 3) if orc > rnd else None
            m["mcnemar_top1_vs_source"] = _paired(sub, source_orders, orders, 1)
            entry["parts"][part] = m
        report["selectors"][name] = entry
        if write:
            dest = os.path.join(out_root, f"{run_name}-sel-{name}")
            write_run(run_dir, dest, cases, orders, infos, sel, seed)
            report["written"].append(dest)
    report["markdown"] = format_markdown(report)
    if write:
        path = os.path.join(out_root, f"{run_name}-selection.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report["markdown"] + "\n")
        with open(path[:-3] + ".json", "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in report.items() if k != "markdown"}, f, indent=2)
        report["written"] += [path, path[:-3] + ".json"]
    return report


def format_markdown(r: dict) -> str:
    lines = [f"## Selection replay on {r['run']} ({r['n_bugs']} bugs, seed {r['seed']})", "",
             "No new model calls for S0/S0r/S1*. Selectors only reorder methods inside the source run's ties.", ""]
    for part, ref in r["parts"].items():
        rnd = ref["random_ties"]
        lines += [f"### {part} ({ref['n']} bugs; infrastructure failures {ref['infra_failures']}; buggy method among "
                  f"the stored candidates in {ref['reachable']})", "",
                  "| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        s, o = ref["source"], ref["oracle"]
        lines.append(f"| source order (S0) | {s['top1']} | {s['top3']} | {s['top5']} | {s['mrr']:.3f} | {s['map']:.3f} | | | | |")
        lines.append(f"| random ties, mean of {rnd['draws']} (95% range) | {rnd['top1']['mean']:.1f} ({rnd['top1']['p2_5']}-"
                     f"{rnd['top1']['p97_5']}) | {rnd['top3']['mean']:.1f} | {rnd['top5']['mean']:.1f} | "
                     f"{rnd['mrr']['mean']:.3f} | {rnd['map']['mean']:.3f} | | | | |")
        lines.append(f"| oracle tie-breaker (bound) | {o['top1']} | {o['top3']} | {o['top5']} | {o['mrr']:.3f} | {o['map']:.3f} | | | | |")
        for name, entry in r["selectors"].items():
            m = entry["parts"][part]
            gap = "" if m["oracle_gap_recovered"] is None else f"{m['oracle_gap_recovered']:.0%}"
            lines.append(f"| {name} | {m['top1']} | {m['top3']} | {m['top5']} | {m['mrr']:.3f} | {m['map']:.3f} | "
                         f"{m['gain_vs_source']:+d} | {m['gain_vs_random']:+.1f} | {gap} | "
                         f"{m['mcnemar_top1_vs_source']['p']:.3f} |")
        lines.append("")
    lines.append("Selectors: " + "; ".join(f"**{n}** = {e['description']}" for n, e in r["selectors"].items()))
    lines.append("")
    lines.append("A Top-1 inside the random-ties 95% range is not evidence of a better selector.")
    if r.get("test_hidden"):
        lines.append("Test part hidden: choose on dev, then run once with --reveal-test.")
    return "\n".join(lines)
