"""Replay selectors on a finished run and write each result as a run folder of its own."""
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from ..compare import mcnemar_exact
from . import agent, judges, metrics, prompts, selectors   # noqa: F401  judges/agent register S5, S2, S5+S2, S6, S8*
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


def _cost(cases: List[BugCase], infos: Dict[str, dict]) -> dict:
    keys = ("calls", "cached_calls", "tokens", "seconds", "pairs", "draws", "position_inconsistent", "no_context",
            "steps", "tool_calls", "invalid_actions", "forced_submit", "unparsed_final", "top1_agree")
    tot = {k: 0 for k in keys}
    judged = 0
    for c in cases:
        info = infos.get(c.bug) or {}
        judged += bool(info.get("shortlist")) and len(info["shortlist"]) > 1
        for k in keys:
            tot[k] += int(info.get(k, 0) or 0) if k != "seconds" else (info.get(k, 0) or 0)
    tot["seconds"] = round(tot["seconds"], 1)
    tot["bugs_judged"] = judged
    tot["calls_per_judged_bug"] = round(tot["calls"] / judged, 1) if judged else 0
    return tot


def _shortlist_oracle(cases: List[BugCase], infos: Dict[str, dict], orders: Dict[str, List[dict]]) -> int:
    """Top-1 reachable by this selector: the buggy method is in the judged shortlist (or already first)."""
    n = 0
    for c in cases:
        short = set((infos.get(c.bug) or {}).get("shortlist") or [])
        first = (orders.get(c.bug) or c.candidates or [{}])[:1]
        n += bool(short & c.truth) or bool(first and first[0].get("method_name") in c.truth)
    return n


def write_run(src_run: str, dest: str, cases: List[BugCase], orders: Dict[str, List[dict]],
              infos: Dict[str, dict], selector: selectors.Selector, seed: int, extra: Optional[dict] = None) -> None:
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
                         "description": selector.description, "seed": seed, "model_calls": selector.model_calls,
                         **(extra or {})}
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
           soapfl_dir: Optional[str] = None, reveal_test: bool = False, client=None, k: int = 8,
           shortlist: str = "top-tie", jobs: int = 1, agent_steps: int = 6, agent_protocol: str = "native",
           context_dir: Optional[str] = None) -> dict:
    """reveal_test=False reports only the dev part of the split: choose selectors and settings on dev, then
    run once with reveal_test=True. Without a split (e.g. HypoDeduce lists, test-only) everything is shown.
    Model-based selectors (S5, S2, S5+S2) need `client` (a JudgeClient); while the test part is hidden they
    only judge the dev bugs (test bugs keep the source order), so no GPU time is spent on hidden bugs."""
    cases = load_cases(run_dir, soapfl_dir, context_dir)
    split = load_split(split_path) if split_path and os.path.exists(split_path) else None
    run_name = os.path.basename(os.path.normpath(run_dir))
    out_root = out_root or os.path.dirname(os.path.normpath(run_dir))
    source_orders = {c.bug: list(c.candidates) for c in cases if c.candidates}
    parts = (["dev", "test", "all"] if reveal_test else ["dev"]) if split else ["all"]
    report = {"run": run_name, "n_bugs": len(cases), "seed": seed, "parts": {}, "selectors": {}, "written": [],
              "with_context": sum(1 for c in cases if c.context),
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
        extra = {}
        if sel.model_calls:
            if client is None:
                raise ValueError(f"selector {name} makes model calls: give a model endpoint (see `select --help`)")
            if isinstance(sel, agent.S8b):
                sel.configure(client, k=k, mode=shortlist, max_steps=agent_steps, protocol=agent_protocol)
            else:
                sel.configure(client, k=k, mode=shortlist)
            extra = {"judge_model": client.model, "shortlist": shortlist, "k": k,
                     "prompt_version": prompts.version(getattr(sel, "uses_evidence", False)),
                     "judged_parts": ["dev"] if report["test_hidden"] else ["all"]}
            if isinstance(sel, agent.S8b):
                import hashlib, inspect
                extra.update({"agent_steps": agent_steps, "agent_protocol": agent_protocol,
                              "agent_version": hashlib.sha256(inspect.getsource(agent).encode()).hexdigest()[:12]})
        todo = [c for c in cases if c.candidates]
        if sel.model_calls and report["test_hidden"]:
            todo = [c for c in todo if part_of(c.bug, split) == "dev"]
        orders = {c.bug: list(c.candidates) for c in cases if c.candidates}
        infos = {c.bug: {"not_judged": True} for c in cases if c.candidates} if sel.model_calls else {}

        def one(c):
            return c.bug, sel.order(c, seed)
        if sel.model_calls and jobs > 1:
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                results = list(pool.map(one, todo))
        else:
            results = []
            for i, c in enumerate(todo, 1):
                results.append(one(c))
                if sel.model_calls:
                    info = results[-1][1][1]
                    print(f"  [{name}] {i}/{len(todo)} {c.bug}: {info.get('calls', 0)} new calls", flush=True)
        for bug, (order, info) in results:
            orders[bug], infos[bug] = order, info
        entry = {"description": sel.description, "parts": {}, **({"settings": extra} if extra else {})}
        for part in parts:
            sub = _subset(cases, split, part)
            m = metrics.evaluate(sub, orders)
            ref = report["parts"][part]
            rnd, orc = ref["random_ties"]["top1"]["mean"], ref["oracle"]["top1"]
            m["gain_vs_source"] = m["top1"] - ref["source"]["top1"]
            m["gain_vs_random"] = round(m["top1"] - rnd, 2)
            m["oracle_gap_recovered"] = round((m["top1"] - rnd) / (orc - rnd), 3) if orc > rnd else None
            m["mcnemar_top1_vs_source"] = _paired(sub, source_orders, orders, 1)
            if sel.model_calls:
                m["cost"] = _cost(sub, infos)
                m["shortlist_oracle_top1"] = _shortlist_oracle(sub, infos, orders)
            entry["parts"][part] = m
        report["selectors"][name] = entry
        if write:
            dest = os.path.join(out_root, f"{run_name}-sel-{name}")
            write_run(run_dir, dest, cases, orders, infos, sel, seed, extra)
            report["written"].append(dest)
    if write:
        _merge_previous(report, os.path.join(out_root, f"{run_name}-selection.json"))
    report["markdown"] = format_markdown(report)
    if write:
        path = os.path.join(out_root, f"{run_name}-selection.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report["markdown"] + "\n")
        with open(path[:-3] + ".json", "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in report.items() if k != "markdown"}, f, indent=2)
        report["written"] += [path, path[:-3] + ".json"]
    return report


def _merge_previous(report: dict, path: str) -> None:
    """Keep selectors of an earlier replay of the same run (same parts shown) in the summary, so running S5 after
    S0/S1 does not drop their rows. Rows of the new run win; nothing is merged if the parts differ."""
    if not os.path.exists(path):
        return
    try:
        old = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if list(old.get("parts", {})) != list(report["parts"]) or old.get("seed") != report["seed"]:
        return
    merged = {n: e for n, e in old.get("selectors", {}).items() if n not in report["selectors"]}
    merged.update(report["selectors"])
    report["selectors"] = merged


def format_markdown(r: dict) -> str:
    lines = [f"## Selection replay on {r['run']} ({r['n_bugs']} bugs, seed {r['seed']})", "",
             "S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors "
             "re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their "
             "bound (see 'Top-1 reachable in shortlist').", ""]
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
        judged = [(n, e) for n, e in r["selectors"].items() if "cost" in e["parts"][part]]
        agent_notes = []
        if judged:
            lines += ["Model-based selectors, cost and reach on this part:", "",
                      "| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | "
                      "pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |",
                      "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
            for n, e in judged:
                c, st = e["parts"][part]["cost"], e.get("settings", {})
                c = {k: c.get(k, 0) for k in ("calls", "cached_calls", "tokens", "seconds", "pairs", "draws",
                                              "position_inconsistent", "no_context", "steps", "tool_calls",
                                              "invalid_actions", "forced_submit", "unparsed_final", "top1_agree",
                                              "bugs_judged")}   # rows merged from older summaries lack new keys
                pairs = f"{c['draws']} / {c['pairs']} ({c['position_inconsistent']})" if c["pairs"] else ""
                judged_txt = f"{c['bugs_judged']}" + (f" (no context: {c['no_context']})" if c["no_context"] else "")
                lines.append(f"| {n} | {st.get('judge_model', '')} | {st.get('shortlist', '')} ({st.get('k', '')}) | "
                             f"{judged_txt} | {c['calls']} | {c['cached_calls']} | {c['tokens']} | {c['seconds']} | "
                             f"{pairs} | {e['parts'][part].get('shortlist_oracle_top1', '')} |")
                if c["steps"]:
                    agent_notes.append(f"{n}: {c['steps']} agent turns, {c['tool_calls']} tool calls, "
                                       f"{c['invalid_actions']} invalid actions, {c['forced_submit']} forced submits, "
                                       f"{c['unparsed_final']} unparsed final answers, forward/reversed top-1 agree in "
                                       f"{c['top1_agree']} of {c['bugs_judged']} bugs")
            lines.append("")
            if agent_notes:
                lines += ["Agent behaviour: " + "; ".join(agent_notes), ""]
    lines.append("Selectors: " + "; ".join(f"**{n}** = {e['description']}" for n, e in r["selectors"].items()))
    lines.append("")
    lines.append("A Top-1 inside the random-ties 95% range is not evidence of a better selector.")
    if r.get("test_hidden"):
        lines.append("Test part hidden: choose on dev, then run once with --reveal-test.")
    return "\n".join(lines)
