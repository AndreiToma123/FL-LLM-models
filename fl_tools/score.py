"""Top-N scoring of a SoapFL run, computed exactly like SoapFL's Evaluation/evaluate.py.

Rank of a bug = 1-based position of the first reviewed method that is one of the
bug's modified methods, in the order stored in result.json (SoapFL sorts that list
by score, descending; ties keep review order). Top-N counts bugs with rank <= N.
A bug without result.json counts as not localised, and the denominator is every
bug that was attempted (not only those that produced output).
"""
import csv
import json
import os
from collections import OrderedDict
from typing import Dict, List, Optional

from .results import BugRecord, load_records

# SoapFL paper, Table II, GPT-3.5, all 395 Defects4J 1.2.0 bugs. NOT comparable
# to a subset; shown only as a rough reference.
PAPER_SOAPFL_GPT35 = {"n_bugs": 395, "top1": 175, "top3": 232, "top5": 236}

SOAPFL_CSV_HEADER = ["project", "bug_id", "true_class", "true_method", "method_rank",
                     "recall_ratio", "false_positive", "cost", "total_tokens", "time"]


def rank_bug(result: dict, buggy_methods: List[str]) -> dict:
    """Port of get_metrics() from SoapFL's Evaluation/evaluate.py."""
    buggy_classes = [m.split("::")[0].split("$")[0] for m in buggy_methods]
    ranked = result.get("buggy_methods", [])
    true_class = 0
    method_rank: Optional[int] = None
    for position, entry in enumerate(ranked, start=1):
        if entry.get("class_name") in buggy_classes:
            true_class = 1
        if entry.get("method_name") in buggy_methods:
            method_rank = position
            break
    recall = fp = 0
    for name in result.get("buggy_codes", {}):
        if name in buggy_methods:
            recall += 1
        else:
            fp += 1
    return {
        "true_class": true_class,
        "true_method": 1 if method_rank == 1 else 0,
        "method_rank": method_rank,
        "recall_ratio": f"{recall}|{len(buggy_methods)}",
        "false_positive": fp,
    }


def token_totals(record: BugRecord) -> Dict[str, float]:
    calls = record.llm_calls
    return {
        "llm_calls": len(calls),
        "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls),
        "completion_tokens": sum(c.get("completion_tokens") or 0 for c in calls),
        "llm_seconds": round(sum(c.get("latency_s") or 0.0 for c in calls), 2),
    }


def score_record(record: BugRecord) -> dict:
    row = {"project": record.bug.project, "bug_id": record.bug.id,
           "true_class": 0, "true_method": 0, "method_rank": None,
           "recall_ratio": "N/A", "false_positive": 0, "has_result": record.result is not None,
           "has_truth": record.truth is not None}
    if record.result is not None and record.truth is not None:
        row.update(rank_bug(record.result, record.truth))
    totals = token_totals(record)
    row.update(totals)
    row["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    row["wall_s"] = (record.run or {}).get("wall_s")
    row["status"] = (record.run or {}).get("status", "unknown")
    return row


def summarise(rows: List[dict]) -> "OrderedDict[str, dict]":
    """Per-project and overall Top-N counts."""
    out: "OrderedDict[str, dict]" = OrderedDict()

    def bucket(key):
        return out.setdefault(key, {"attempted": 0, "with_result": 0, "class_hit": 0,
                                    "top1": 0, "top3": 0, "top5": 0,
                                    "total_tokens": 0, "llm_calls": 0})

    for row in rows:
        for key in (row["project"], "ALL"):
            b = bucket(key)
            b["attempted"] += 1
            b["with_result"] += int(row["has_result"])
            b["class_hit"] += int(bool(row["true_class"]))
            rank = row["method_rank"]
            b["top1"] += int(rank is not None and rank <= 1)
            b["top3"] += int(rank is not None and rank <= 3)
            b["top5"] += int(rank is not None and rank <= 5)
            b["total_tokens"] += row["total_tokens"]
            b["llm_calls"] += row["llm_calls"]
    # keep ALL last
    all_row = out.pop("ALL", None)
    if all_row is not None:
        out["ALL"] = all_row
    return out


def format_markdown(summary: "OrderedDict[str, dict]", reference: Optional[dict] = None) -> str:
    lines = ["| Project | Attempted | With output | Top-1 | Top-3 | Top-5 | Class hit | Tokens/bug |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for key, b in summary.items():
        n = max(b["attempted"], 1)

        def pct(x):
            return f"{x} ({100 * x / n:.0f}%)"
        lines.append(f"| {key} | {b['attempted']} | {b['with_result']} | {pct(b['top1'])} | "
                     f"{pct(b['top3'])} | {pct(b['top5'])} | {pct(b['class_hit'])} | "
                     f"{b['total_tokens'] // n:,} |")
    lines.append("")
    p = PAPER_SOAPFL_GPT35
    lines.append(f"Reference (SoapFL paper, GPT-3.5, all {p['n_bugs']} bugs): "
                 f"Top-1 {p['top1']} ({100 * p['top1'] / p['n_bugs']:.0f}%), "
                 f"Top-3 {p['top3']} ({100 * p['top3'] / p['n_bugs']:.0f}%), "
                 f"Top-5 {p['top5']} ({100 * p['top5'] / p['n_bugs']:.0f}%). "
                 f"Compare percentages only, and only for large samples.")
    if reference:
        lines.append("")
        lines.append(f"Paired comparison with the reference CSV on the {reference['n_common']} "
                     f"bugs both runs cover:")
        lines.append("")
        lines.append("| | Top-1 | Top-3 | Top-5 |")
        lines.append("|---|---:|---:|---:|")
        lines.append(f"| this run | {reference['ours'][1]} | {reference['ours'][3]} | {reference['ours'][5]} |")
        lines.append(f"| reference | {reference['ref'][1]} | {reference['ref'][3]} | {reference['ref'][5]} |")
        lines.append(f"| Top-1 only this run / only reference / both | "
                     f"{reference['only_ours']} / {reference['only_ref']} / {reference['both']} | | |")
    return "\n".join(lines)


def load_reference_csv(path: str) -> Dict[str, Optional[int]]:
    """SoapFL-format CSV (header + 10 columns) -> {'Lang-1': rank or None}."""
    ranks: Dict[str, Optional[int]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for cols in reader:
            if len(cols) < 5:
                continue
            ranks[f"{cols[0]}-{cols[1]}"] = None if cols[4] in ("N/A", "") else int(cols[4])
    return ranks


def paired_comparison(rows: List[dict], ref_ranks: Dict[str, Optional[int]]) -> Optional[dict]:
    common = [r for r in rows if f"{r['project']}-{r['bug_id']}" in ref_ranks]
    if not common:
        return None

    def count(ranks, n):
        return sum(1 for r in ranks if r is not None and r <= n)
    ours = [r["method_rank"] for r in common]
    ref = [ref_ranks[f"{r['project']}-{r['bug_id']}"] for r in common]
    both = sum(1 for a, b in zip(ours, ref) if a == 1 and b == 1)
    only_ours = sum(1 for a, b in zip(ours, ref) if a == 1 and b != 1)
    only_ref = sum(1 for a, b in zip(ours, ref) if b == 1 and a != 1)
    return {"n_common": len(common),
            "ours": {n: count(ours, n) for n in (1, 3, 5)},
            "ref": {n: count(ref, n) for n in (1, 3, 5)},
            "both": both, "only_ours": only_ours, "only_ref": only_ref}


def write_outputs(run_dir: str, rows: List[dict], summary: dict, markdown: str) -> List[str]:
    written = []
    detail = os.path.join(run_dir, "per_bug.csv")
    fields = ["project", "bug_id", "status", "has_result", "has_truth", "method_rank", "true_class",
              "recall_ratio", "false_positive", "llm_calls", "prompt_tokens", "completion_tokens",
              "total_tokens", "llm_seconds", "wall_s"]
    with open(detail, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "method_rank": "N/A" if row["method_rank"] is None else row["method_rank"]})
    written.append(detail)

    # exactly the 10-column format SoapFL's Evaluation/*.py scripts read
    compat = os.path.join(run_dir, "per_bug_soapfl_format.csv")
    with open(compat, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(SOAPFL_CSV_HEADER)
        for row in rows:
            if not row["has_result"]:
                continue
            writer.writerow([row["project"], row["bug_id"], row["true_class"], row["true_method"],
                             "N/A" if row["method_rank"] is None else row["method_rank"],
                             row["recall_ratio"], row["false_positive"], 0,
                             row["total_tokens"], row["llm_seconds"]])
    written.append(compat)

    summary_json = os.path.join(run_dir, "summary.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    written.append(summary_json)
    summary_md = os.path.join(run_dir, "summary.md")
    with open(summary_md, "w", encoding="utf-8") as f:
        f.write(markdown + "\n")
    written.append(summary_md)
    return written


def score_run(run_dir: str, soapfl_dir: Optional[str] = None, reference_csv: Optional[str] = None,
              write: bool = True) -> dict:
    records = load_records(run_dir, soapfl_dir)
    rows = [score_record(r) for r in records]
    summary = summarise(rows)
    paired = None
    if reference_csv:
        paired = paired_comparison(rows, load_reference_csv(reference_csv))
    markdown = format_markdown(summary, paired)
    written = write_outputs(run_dir, rows, summary, markdown) if write else []
    no_truth = [f"{r['project']}-{r['bug_id']}" for r in rows if r["has_result"] and not r["has_truth"]]
    return {"rows": rows, "summary": summary, "markdown": markdown, "written": written,
            "missing_truth": no_truth}
