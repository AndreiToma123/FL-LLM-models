"""Failure-funnel analysis: at which pipeline stage is each bug lost?

Stages, in the order SoapFL executes them::

    attempted
      -> produced a ranking        (otherwise: crashed / no_valid_class / context_overflow / ...)
      -> right class selected      (otherwise: class_missed)
      -> buggy method reached the  (otherwise: method_filtered_out; the method filter or the
         review stage                class-level doc/method-list step dropped it)
      -> ranked in the top 5       (otherwise: ranked_below_5)
      -> ranked first              (otherwise: rank_2_5)

This mirrors the funnel analysis HypoDeduce (ICSE-NIER 2026) ran on SoapFL, so the
numbers can be discussed side by side. Because SoapFL breaks score ties by review
order, each Top-1 is also checked for tie-dependence.
"""
import csv
import json
import os
from collections import Counter, OrderedDict
from typing import Dict, List, Optional

from .results import BugRecord, load_records

TERMINAL_STAGES = ["not_run", "crashed", "no_valid_class", "context_overflow", "no_valid_method",
                   "empty_unknown", "no_ground_truth", "class_missed", "method_filtered_out",
                   "ranked_below_5", "rank_2_5", "top1"]


def _ties(ranked: List[dict], rank: int) -> int:
    """How many reviewed methods share the score of the buggy method (including itself)."""
    score = ranked[rank - 1].get("score")
    return sum(1 for m in ranked if m.get("score") == score)


def classify(record: BugRecord) -> dict:
    """Assign one terminal stage to a bug and collect supporting facts."""
    info = {"bug": record.bug.name, "project": record.bug.project, "stage": None,
            "detail": "", "rank": None, "tie_group": None, "n_reviewed": 0}

    if record.dir is None and record.run is None:
        info["stage"] = "not_run"
        return info

    if record.result is None:
        run = record.run or {}
        if run.get("status") == "failed" or run.get("status") == "timeout":
            info["stage"] = "crashed"
            info["detail"] = run.get("error_class") or run.get("status")
        elif record.events_of("no_valid_class"):
            info["stage"] = "no_valid_class"
        elif record.events_of("terminated") or record.events_of("context_overflow_guard"):
            info["stage"] = "context_overflow"
        elif record.events_of("no_valid_method"):
            info["stage"] = "no_valid_method"
        else:
            info["stage"] = "empty_unknown"
        return info

    if record.truth is None:
        info["stage"] = "no_ground_truth"
        return info

    ranked = record.result.get("buggy_methods", [])
    info["n_reviewed"] = len(ranked)
    truth = set(record.truth)
    truth_classes = {m.split("::")[0].split("$")[0] for m in truth}
    selected_classes = {m.get("class_name") for m in ranked}

    if not (selected_classes & truth_classes):
        info["stage"] = "class_missed"
        return info

    rank = next((i for i, m in enumerate(ranked, start=1) if m.get("method_name") in truth), None)
    if rank is None:
        info["stage"] = "method_filtered_out"
        return info

    info["rank"] = rank
    info["tie_group"] = _ties(ranked, rank)
    if rank == 1:
        info["stage"] = "top1"
    elif rank <= 5:
        info["stage"] = "rank_2_5"
    else:
        info["stage"] = "ranked_below_5"
    return info


def event_stats(records: List[BugRecord]) -> Dict[str, float]:
    kinds = Counter()
    finish = Counter()
    prompt_tokens: List[int] = []
    think_calls = 0
    for record in records:
        for event in record.events:
            kinds[event.get("type")] += 1
            if event.get("type") == "llm_call":
                finish[event.get("finish_reason")] += 1
                if event.get("prompt_tokens"):
                    prompt_tokens.append(event["prompt_tokens"])
                if event.get("think_chars_removed"):
                    think_calls += 1
    return {
        "llm_calls": kinds.get("llm_call", 0),
        "calls_truncated_by_length": finish.get("length", 0),
        "calls_with_think_block": think_calls,
        "score_unparsed": kinds.get("score_unparsed", 0),
        "no_valid_class": kinds.get("no_valid_class", 0),
        "no_valid_method": kinds.get("no_valid_method", 0),
        "terminated_phases": kinds.get("terminated", 0),
        "context_overflow_guard": kinds.get("context_overflow_guard", 0),
        "max_prompt_tokens": max(prompt_tokens) if prompt_tokens else 0,
        "mean_prompt_tokens": round(sum(prompt_tokens) / len(prompt_tokens)) if prompt_tokens else 0,
    }


def funnel_counts(infos: List[dict]) -> "OrderedDict[str, int]":
    """Cumulative counts: how many bugs survive each stage."""
    n = len(infos)
    produced = [i for i in infos if i["stage"] in
                ("no_ground_truth", "class_missed", "method_filtered_out", "ranked_below_5", "rank_2_5", "top1")]
    labelled = [i for i in produced if i["stage"] != "no_ground_truth"]
    class_ok = [i for i in labelled if i["stage"] != "class_missed"]
    reached = [i for i in class_ok if i["stage"] != "method_filtered_out"]
    top5 = [i for i in reached if i["stage"] in ("rank_2_5", "top1")]
    top1 = [i for i in reached if i["stage"] == "top1"]
    return OrderedDict([
        ("attempted", n),
        ("produced a ranking", len(produced)),
        ("right class selected", len(class_ok)),
        ("buggy method reached ranking", len(reached)),
        ("ranked in top 5", len(top5)),
        ("ranked first", len(top1)),
    ])


def format_markdown(infos: List[dict], stats: Dict[str, float]) -> str:
    counts = funnel_counts(infos)
    n = max(counts["attempted"], 1)
    lines = ["## Funnel", "", "| Stage | Bugs | % of attempted |", "|---|---:|---:|"]
    for stage, count in counts.items():
        lines.append(f"| {stage} | {count} | {100 * count / n:.0f}% |")

    lines += ["", "## Where bugs were lost", "", "| Terminal stage | Bugs |", "|---|---:|"]
    by_stage = Counter(i["stage"] for i in infos)
    for stage in TERMINAL_STAGES:
        if by_stage.get(stage):
            lines.append(f"| {stage} | {by_stage[stage]} |")

    crashed = Counter(i["detail"] for i in infos if i["stage"] == "crashed")
    if crashed:
        lines += ["", "Crash reasons: " + ", ".join(f"{k or 'unknown'}: {v}" for k, v in crashed.most_common())]

    top1 = [i for i in infos if i["stage"] == "top1"]
    if top1:
        tied = sum(1 for i in top1 if (i["tie_group"] or 1) > 1)
        lines += ["", f"Tie-dependence: {tied} of {len(top1)} Top-1 hits share their score with at "
                      f"least one other reviewed method, so they depend on review order."]

    lines += ["", "## Events", "", "| Event | Count |", "|---|---:|"]
    for key, value in stats.items():
        lines.append(f"| {key} | {value:,} |")

    per_project: Dict[str, Counter] = {}
    for i in infos:
        per_project.setdefault(i["project"], Counter())[i["stage"]] += 1
    lines += ["", "## Per project", "",
              "| Project | Attempted | " + " | ".join(s for s in TERMINAL_STAGES if by_stage.get(s)) + " |",
              "|---|---:|" + "---:|" * len([s for s in TERMINAL_STAGES if by_stage.get(s)])]
    for project, counter in sorted(per_project.items()):
        cells = " | ".join(str(counter.get(s, 0)) for s in TERMINAL_STAGES if by_stage.get(s))
        lines.append(f"| {project} | {sum(counter.values())} | {cells} |")
    return "\n".join(lines)


def analyse_run(run_dir: str, soapfl_dir: Optional[str] = None, write: bool = True) -> dict:
    records = load_records(run_dir, soapfl_dir)
    infos = [classify(r) for r in records]
    stats = event_stats(records)
    markdown = format_markdown(infos, stats)
    written: List[str] = []
    if write:
        md_path = os.path.join(run_dir, "funnel.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown + "\n")
        csv_path = os.path.join(run_dir, "funnel_per_bug.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["bug", "project", "stage", "detail", "rank",
                                                   "tie_group", "n_reviewed"])
            writer.writeheader()
            writer.writerows(infos)
        json_path = os.path.join(run_dir, "funnel.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"funnel": funnel_counts(infos), "events": stats}, f, indent=2)
        written = [md_path, csv_path, json_path]
    return {"infos": infos, "events": stats, "markdown": markdown, "written": written}
