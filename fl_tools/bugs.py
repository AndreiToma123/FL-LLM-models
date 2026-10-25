"""Defects4J bug lists (two datasets) and deterministic sampling.

Dataset 1, ``d4j14`` (default): Defects4J 1.4.0 as run by SoapFL's authors.
Dataset 2, ``d4j2new``: the bugs Defects4J 2.0 ADDED (444 bugs: 11 new projects + Closure 134-176). Defects4J is
installed at commit 4c41759 (2022-08-25, between v2.0.0 and v2.0.1): the exact base of SoapFL's own
``Defects4J_mod/defects4j-2.0.0-jvm-mod`` overlay (verified by diff). Directory names use ``d4j2.0.0-...`` like
SoapFL. The table is the active bug list of that commit; SoapFL's run_all.py has a commented-out 2.0.0 table that
leaves out Gson, JacksonCore and Jsoup 1-45 (no reason given); we keep them and report failures.

Dataset 1 details:

The table below is copied from SoapFL's own run_all.py (the active ``D4J`` dict),
so a full run covers exactly the bugs SoapFL's authors ran. Note that it skips
seven "deprecated" bug IDs, which gives 388 bugs, whereas the SoapFL paper's
Table I lists 395. Use ``include_deprecated=True`` to get all 395 IDs.
"""
import random
import re
from dataclasses import dataclass
import os
from typing import Dict, Iterable, List, Optional, Sequence

VERSION = "1.4.0"          # dataset 1 (kept for backwards compatibility)

# project -> (first id, last id, deprecated ids skipped by SoapFL's run_all.py)
D4J: Dict[str, dict] = {
    "Time":    {"begin": 1, "end": 27,  "deprecate": [21]},
    "Chart":   {"begin": 1, "end": 26,  "deprecate": []},
    "Lang":    {"begin": 1, "end": 65,  "deprecate": [2, 18, 25, 48]},
    "Mockito": {"begin": 1, "end": 38,  "deprecate": []},
    "Math":    {"begin": 1, "end": 106, "deprecate": []},
    "Closure": {"begin": 1, "end": 133, "deprecate": [63, 93]},
}


# Defects4J 2.0 (commit 4c41759), bugs not in 1.4.0; ids from framework/projects/<P>/active-bugs.csv
D4J2_NEW: Dict[str, dict] = {
    "Cli":             {"begin": 1,   "end": 40,  "deprecate": [6]},
    "Closure":         {"begin": 134, "end": 176, "deprecate": []},
    "Codec":           {"begin": 1,   "end": 18,  "deprecate": []},
    "Collections":     {"begin": 25,  "end": 28,  "deprecate": []},
    "Compress":        {"begin": 1,   "end": 47,  "deprecate": []},
    "Csv":             {"begin": 1,   "end": 16,  "deprecate": []},
    "Gson":            {"begin": 1,   "end": 18,  "deprecate": []},
    "JacksonCore":     {"begin": 1,   "end": 26,  "deprecate": []},
    "JacksonDatabind": {"begin": 1,   "end": 112, "deprecate": []},
    "JacksonXml":      {"begin": 1,   "end": 6,   "deprecate": []},
    "Jsoup":           {"begin": 1,   "end": 93,  "deprecate": []},
    "JxPath":          {"begin": 1,   "end": 22,  "deprecate": []},
}

DATASETS: Dict[str, dict] = {
    "d4j14":   {"version": "1.4.0", "table": D4J, "home_env": "DEFECTS4J_HOME", "home": "/opt/defects4j",
                "label": "Defects4J 1.4.0 (SoapFL's 388 bugs)"},
    "d4j2new": {"version": "2.0.0", "table": D4J2_NEW, "home_env": "DEFECTS4J2_HOME", "home": "/opt/defects4j-2",
                "label": "Defects4J 2.0 new bugs (444)"},
}
DEFAULT_DATASET = "d4j14"
VERSION_TO_DATASET = {d["version"]: k for k, d in DATASETS.items()}


def dataset_of_version(version: str) -> str:
    if version not in VERSION_TO_DATASET:
        raise ValueError(f"unknown Defects4J version {version!r}; known: {', '.join(VERSION_TO_DATASET)}")
    return VERSION_TO_DATASET[version]


def defects4j_home(dataset_or_version: str) -> Optional[str]:
    """Defects4J installation for a dataset: its env variable, else the image default if present."""
    key = dataset_or_version if dataset_or_version in DATASETS else dataset_of_version(dataset_or_version)
    d = DATASETS[key]
    home = os.environ.get(d["home_env"]) or d["home"]
    return home if os.path.isdir(home) else None


@dataclass(frozen=True, order=True)
class Bug:
    project: str
    id: int
    version: str = VERSION

    @property
    def name(self) -> str:
        return f"{self.project}-{self.id}"

    @property
    def dirname(self) -> str:
        """Directory name SoapFL's run.py uses for this bug."""
        return f"d4j{self.version}-{self.project}-{self.id}"

    def __str__(self) -> str:
        return self.name


def _table(dataset: str) -> Dict[str, dict]:
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}; known: {', '.join(DATASETS)}")
    return DATASETS[dataset]["table"]


def project_bugs(project: str, include_deprecated: bool = False, dataset: str = DEFAULT_DATASET) -> List[Bug]:
    spec = _table(dataset)[project]
    version = DATASETS[dataset]["version"]
    skip = set() if include_deprecated else set(spec["deprecate"])
    return [Bug(project, i, version) for i in range(spec["begin"], spec["end"] + 1) if i not in skip]


def all_bugs(include_deprecated: bool = False, dataset: str = DEFAULT_DATASET) -> List[Bug]:
    out: List[Bug] = []
    for project in _table(dataset):
        out.extend(project_bugs(project, include_deprecated, dataset))
    return out


def bug_from_dirname(dirname: str) -> Bug:
    """'d4j1.4.0-Lang-12' -> Bug('Lang', 12, '1.4.0')."""
    match = re.fullmatch(r"d4j([\d.]+)-([A-Za-z]+)-(\d+)", dirname)
    if not match:
        raise ValueError(f"not a SoapFL result directory name: {dirname!r}")
    return Bug(match.group(2), int(match.group(3)), match.group(1))


def parse_bugs(spec: str, include_deprecated: bool = False, dataset: str = DEFAULT_DATASET) -> List[Bug]:
    """Parse ``Lang-1,Math-3,Chart-1:5,Time`` into bugs of one dataset.

    ``Project-N`` is one bug, ``Project-A:B`` an inclusive range, and a bare
    ``Project`` every bug of that project.
    """
    table = _table(dataset)
    version = DATASETS[dataset]["version"]
    bugs: List[Bug] = []
    for token in (t.strip() for t in spec.split(",")):
        if not token:
            continue
        match = re.fullmatch(r"([A-Za-z]+)(?:-(\d+)(?::(\d+))?)?", token)
        if not match or match.group(1) not in table:
            raise ValueError(f"cannot parse bug selector {token!r}; known projects in {dataset}: {', '.join(table)}")
        project, first, last = match.group(1), match.group(2), match.group(3)
        if first is None:
            bugs.extend(project_bugs(project, include_deprecated, dataset))
            continue
        lo, hi = int(first), int(last) if last else int(first)
        if lo > hi:
            raise ValueError(f"empty range in {token!r}")
        valid = {b.id for b in project_bugs(project, include_deprecated=True, dataset=dataset)}
        for i in range(lo, hi + 1):
            if i not in valid:
                raise ValueError(f"{project}-{i} does not exist in dataset {dataset} (Defects4J {version})")
            bugs.append(Bug(project, i, version))
    # de-duplicate, keep first-seen order
    return list(dict.fromkeys(bugs))


def stratified_sample(bugs: Sequence[Bug], n: int, seed: int = 0, legacy: bool = True) -> List[Bug]:
    """Pick ``n`` bugs spread over projects proportionally to project size.

    Deterministic for a given (bugs, n, seed). Every project gets at least one
    bug when ``n`` is at least the number of projects. The result is returned in
    canonical (project order, id) order.
    """
    if n >= len(bugs):
        return list(bugs)
    if n <= 0:
        return []
    by_project: Dict[str, List[Bug]] = {}
    for bug in bugs:
        by_project.setdefault(bug.project, []).append(bug)
    projects = list(by_project)
    total = len(bugs)

    # largest-remainder allocation
    exact = {p: n * len(by_project[p]) / total for p in projects}
    alloc = {p: int(exact[p]) for p in projects}
    if n >= len(projects):
        for p in projects:
            alloc[p] = max(alloc[p], 1)
    # fix the total up or down
    def remainder(p):
        return exact[p] - int(exact[p])
    if legacy:
        # Kept unchanged so dataset-1 samples (the 100 baseline bugs) stay reproducible. Known flaw: the remainder
        # is not updated after a project gets an extra bug, so ONE project receives all extra bugs (the 100-bug
        # sample has Mockito 13 instead of a proportional 10).
        while sum(alloc.values()) < n:
            candidates = [p for p in projects if alloc[p] < len(by_project[p])]
            alloc[max(candidates, key=lambda p: (remainder(p), len(by_project[p])))] += 1
    else:
        # proper largest-remainder: each project gets at most one extra bug per round, largest remainder first
        while sum(alloc.values()) < n:
            room = [p for p in projects if alloc[p] < len(by_project[p])]
            for p in sorted(room, key=lambda p: (-(exact[p] - alloc[p]), -len(by_project[p]))):
                if sum(alloc.values()) >= n:
                    break
                alloc[p] += 1
    while sum(alloc.values()) > n:
        candidates = [p for p in projects if alloc[p] > (1 if n >= len(projects) else 0)]
        alloc[min(candidates, key=lambda p: (remainder(p), -len(by_project[p])))] -= 1

    rng = random.Random(seed)
    chosen: List[Bug] = []
    for p in projects:
        chosen.extend(rng.sample(by_project[p], alloc[p]))
    order = {p: i for i, p in enumerate(list(D4J) + [p for p in D4J2_NEW if p not in D4J])}
    return sorted(chosen, key=lambda b: (order.get(b.project, 99), b.id))


def select_bugs(bugs_spec: str = "", pilot: int = 0, seed: int = 0, exclude: str = "",
                include_deprecated: bool = False, subset_of: int = 0, dataset: str = DEFAULT_DATASET) -> List[Bug]:
    """Resolve CLI selection flags to a bug list.

    subset_of: draw the pilot sample from the stratified sample of that size (e.g. 10 bugs out of the
    same 100 the baselines used), so small runs can be compared bug by bug with the big ones.
    """
    bugs = parse_bugs(bugs_spec, include_deprecated, dataset) if bugs_spec else all_bugs(include_deprecated, dataset)
    if exclude:
        drop = set(parse_bugs(exclude, include_deprecated=True, dataset=dataset))
        bugs = [b for b in bugs if b not in drop]
    legacy = dataset == "d4j14"
    if subset_of:
        bugs = stratified_sample(bugs, subset_of, seed, legacy)
    if pilot:
        bugs = stratified_sample(bugs, pilot, seed, legacy)
    return bugs


def count_by_project(bugs: Iterable[Bug]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for bug in bugs:
        counts[bug.project] = counts.get(bug.project, 0) + 1
    return counts
