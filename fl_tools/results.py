"""Read the files a batch run leaves behind (shared by score.py and funnel.py).

Layout of one run directory::

    results/<name>/
        run_meta.json            what the run was configured with
        runs.jsonl               one line per attempt (status, wall time, error class)
        _logs/<Project-N>.log    stdout/stderr of SoapFL's run.py
        d4j1.4.0-<Project>-<N>/  SoapFL's own output for one bug:
            result.json          ranked suspicious methods (only written if non-empty)
            events.jsonl         LLM calls and parse/overflow events (added by our patch)
            ground_truth.json    buggy methods, snapshotted from SoapFL's cache
            checkpoint/ log/ post_info_*.txt ...
"""
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .bugs import Bug, bug_from_dirname


def read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_jsonl(path: str) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a half-written last line must not break scoring
    except OSError:
        pass
    return rows


def load_runs(run_dir: str) -> Dict[str, dict]:
    """Latest attempt per bug name from runs.jsonl."""
    latest: Dict[str, dict] = {}
    for row in read_jsonl(os.path.join(run_dir, "runs.jsonl")):
        if "bug" in row:
            latest[row["bug"]] = row
    return latest


def discover_bug_dirs(run_dir: str) -> Dict[str, str]:
    """bug name -> directory, for every SoapFL output folder under run_dir."""
    found: Dict[str, str] = {}
    exported = os.path.join(run_dir, "bugs")   # layout written by `export` (reports/<run>/bugs/<bug>/)
    if os.path.isdir(exported) and not any(e.startswith("d4j") for e in os.listdir(run_dir)):
        run_dir = exported
    try:
        entries = sorted(os.listdir(run_dir))
    except OSError:
        return found
    for entry in entries:
        path = os.path.join(run_dir, entry)
        if os.path.isdir(path) and entry.startswith("d4j"):
            try:
                found[bug_from_dirname(entry).name] = path
            except ValueError:
                continue
    return found


_SNAPSHOT_SCRIPT = r"""
import json, pickle, sys
soapfl, pkl = sys.argv[1], sys.argv[2]
sys.path.insert(0, soapfl)
with open(pkl, "rb") as f:
    failure = pickle.load(f)
print(json.dumps({"buggy_methods": list(failure.buggy_methods or []),
                  "n_test_suites": len(failure.test_suites)}))
"""


def snapshot_ground_truth(soapfl_dir: str, bug_dir: str, python: Optional[str] = None) -> Optional[dict]:
    """Copy the buggy-method labels out of SoapFL's pickled cache into the bug directory.

    Done in a subprocess because unpickling needs SoapFL's classes on sys.path.
    Returns the written dict, or None if the cache file does not exist / fails to load.
    """
    target = os.path.join(bug_dir, "ground_truth.json")
    existing = read_json(target)
    if existing is not None:
        return existing
    pkl = os.path.join(soapfl_dir, "cache", os.path.basename(bug_dir.rstrip(os.sep)), "test_failure.pkl")
    if not os.path.exists(pkl):
        return None
    proc = subprocess.run([python or sys.executable, "-I", "-c", _SNAPSHOT_SCRIPT, soapfl_dir, pkl],
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return None
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


@dataclass
class BugRecord:
    bug: Bug
    dir: Optional[str]
    result: Optional[dict] = None
    truth: Optional[List[str]] = None
    events: List[dict] = field(default_factory=list)
    run: Optional[dict] = None

    def events_of(self, kind: str) -> List[dict]:
        return [e for e in self.events if e.get("type") == kind]

    @property
    def llm_calls(self) -> List[dict]:
        return self.events_of("llm_call")


def load_records(run_dir: str, soapfl_dir: Optional[str] = None,
                 only: Optional[List[Bug]] = None) -> List[BugRecord]:
    """Load every bug that has either an output directory or a runs.jsonl entry."""
    dirs = discover_bug_dirs(run_dir)
    runs = load_runs(run_dir)
    names = set(dirs) | set(runs)
    if only is not None:
        names &= {b.name for b in only}
    records: List[BugRecord] = []
    for name in sorted(names, key=lambda n: (n.split("-")[0], int(n.split("-")[1]))):
        project, bug_id = name.split("-")
        bug = Bug(project, int(bug_id))
        bug_dir = dirs.get(name)
        record = BugRecord(bug=bug, dir=bug_dir, run=runs.get(name))
        if bug_dir:
            record.result = read_json(os.path.join(bug_dir, "result.json"))
            truth = read_json(os.path.join(bug_dir, "ground_truth.json"))
            if truth is None and soapfl_dir:
                truth = snapshot_ground_truth(soapfl_dir, bug_dir)
            if truth is not None:
                record.truth = truth.get("buggy_methods")
            record.events = read_jsonl(os.path.join(bug_dir, "events.jsonl"))
        records.append(record)
    return records
