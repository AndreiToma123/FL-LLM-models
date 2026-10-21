"""Copy the small, useful files of a run (no Defects4J checkouts) to a folder, e.g. one that is shared with Windows."""
import os
import shutil
from typing import List

TOP_FILES = ("run_meta.json", "runs.jsonl", "summary.md", "summary.json", "per_bug.csv",
             "per_bug_soapfl_format.csv", "funnel.md", "funnel.json", "funnel_per_bug.csv")
BUG_FILES = ("result.json", "events.jsonl", "ground_truth.json")


def export_run(run_dir: str, dest: str, include_logs: bool = True) -> List[str]:
    copied: List[str] = []
    os.makedirs(dest, exist_ok=True)
    for name in TOP_FILES:
        src = os.path.join(run_dir, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, name))
            copied.append(name)
    if include_logs and os.path.isdir(os.path.join(run_dir, "_logs")):
        shutil.copytree(os.path.join(run_dir, "_logs"), os.path.join(dest, "_logs"), dirs_exist_ok=True)
        copied.append("_logs/")
    for entry in sorted(os.listdir(run_dir)):
        bug_dir = os.path.join(run_dir, entry)
        if not (entry.startswith("d4j") and os.path.isdir(bug_dir)):
            continue
        out = os.path.join(dest, "bugs", entry)
        for name in BUG_FILES:
            src = os.path.join(bug_dir, name)
            if os.path.exists(src):
                os.makedirs(out, exist_ok=True)
                shutil.copy2(src, os.path.join(out, name))
                copied.append(f"bugs/{entry}/{name}")
    return copied
