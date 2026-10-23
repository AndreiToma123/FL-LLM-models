"""Defects4J 1.4.0 bug list and deterministic sampling.

The table below is copied from SoapFL's own run_all.py (the active ``D4J`` dict),
so a full run covers exactly the bugs SoapFL's authors ran. Note that it skips
seven "deprecated" bug IDs, which gives 388 bugs, whereas the SoapFL paper's
Table I lists 395. Use ``include_deprecated=True`` to get all 395 IDs.
"""
import random
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

VERSION = "1.4.0"

# project -> (first id, last id, deprecated ids skipped by SoapFL's run_all.py)
D4J: Dict[str, dict] = {
    "Time":    {"begin": 1, "end": 27,  "deprecate": [21]},
    "Chart":   {"begin": 1, "end": 26,  "deprecate": []},
    "Lang":    {"begin": 1, "end": 65,  "deprecate": [2, 18, 25, 48]},
    "Mockito": {"begin": 1, "end": 38,  "deprecate": []},
    "Math":    {"begin": 1, "end": 106, "deprecate": []},
    "Closure": {"begin": 1, "end": 133, "deprecate": [63, 93]},
}


@dataclass(frozen=True, order=True)
class Bug:
    project: str
    id: int

    @property
    def name(self) -> str:
        return f"{self.project}-{self.id}"

    @property
    def dirname(self) -> str:
        """Directory name SoapFL's run.py uses for this bug."""
        return f"d4j{VERSION}-{self.project}-{self.id}"

    def __str__(self) -> str:
        return self.name


def project_bugs(project: str, include_deprecated: bool = False) -> List[Bug]:
    spec = D4J[project]
    skip = set() if include_deprecated else set(spec["deprecate"])
    return [Bug(project, i) for i in range(spec["begin"], spec["end"] + 1) if i not in skip]


def all_bugs(include_deprecated: bool = False) -> List[Bug]:
    out: List[Bug] = []
    for project in D4J:
        out.extend(project_bugs(project, include_deprecated))
    return out


def bug_from_dirname(dirname: str) -> Bug:
    """'d4j1.4.0-Lang-12' -> Bug('Lang', 12)."""
    match = re.fullmatch(r"d4j[\d.]+-([A-Za-z]+)-(\d+)", dirname)
    if not match:
        raise ValueError(f"not a SoapFL result directory name: {dirname!r}")
    return Bug(match.group(1), int(match.group(2)))


def parse_bugs(spec: str, include_deprecated: bool = False) -> List[Bug]:
    """Parse ``Lang-1,Math-3,Chart-1:5,Time`` into bugs.

    ``Project-N`` is one bug, ``Project-A:B`` an inclusive range, and a bare
    ``Project`` every bug of that project.
    """
    bugs: List[Bug] = []
    for token in (t.strip() for t in spec.split(",")):
        if not token:
            continue
        match = re.fullmatch(r"([A-Za-z]+)(?:-(\d+)(?::(\d+))?)?", token)
        if not match or match.group(1) not in D4J:
            raise ValueError(f"cannot parse bug selector {token!r}; known projects: {', '.join(D4J)}")
        project, first, last = match.group(1), match.group(2), match.group(3)
        if first is None:
            bugs.extend(project_bugs(project, include_deprecated))
            continue
        lo, hi = int(first), int(last) if last else int(first)
        if lo > hi:
            raise ValueError(f"empty range in {token!r}")
        valid = {b.id for b in project_bugs(project, include_deprecated=True)}
        for i in range(lo, hi + 1):
            if i not in valid:
                raise ValueError(f"{project}-{i} does not exist in Defects4J {VERSION}")
            bugs.append(Bug(project, i))
    # de-duplicate, keep first-seen order
    return list(dict.fromkeys(bugs))


def stratified_sample(bugs: Sequence[Bug], n: int, seed: int = 0) -> List[Bug]:
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
    while sum(alloc.values()) < n:
        candidates = [p for p in projects if alloc[p] < len(by_project[p])]
        alloc[max(candidates, key=lambda p: (remainder(p), len(by_project[p])))] += 1
    while sum(alloc.values()) > n:
        candidates = [p for p in projects if alloc[p] > (1 if n >= len(projects) else 0)]
        alloc[min(candidates, key=lambda p: (remainder(p), -len(by_project[p])))] -= 1

    rng = random.Random(seed)
    chosen: List[Bug] = []
    for p in projects:
        chosen.extend(rng.sample(by_project[p], alloc[p]))
    order = {p: i for i, p in enumerate(D4J)}
    return sorted(chosen, key=lambda b: (order.get(b.project, 99), b.id))


def select_bugs(bugs_spec: str = "", pilot: int = 0, seed: int = 0, exclude: str = "",
                include_deprecated: bool = False, subset_of: int = 0) -> List[Bug]:
    """Resolve CLI selection flags to a bug list.

    subset_of: draw the pilot sample from the stratified sample of that size (e.g. 10 bugs out of the
    same 100 the baselines used), so small runs can be compared bug by bug with the big ones.
    """
    bugs = parse_bugs(bugs_spec, include_deprecated) if bugs_spec else all_bugs(include_deprecated)
    if exclude:
        drop = set(parse_bugs(exclude, include_deprecated=True))
        bugs = [b for b in bugs if b not in drop]
    if subset_of:
        bugs = stratified_sample(bugs, subset_of, seed)
    if pilot:
        bugs = stratified_sample(bugs, pilot, seed)
    return bugs


def count_by_project(bugs: Iterable[Bug]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for bug in bugs:
        counts[bug.project] = counts.get(bug.project, 0) + 1
    return counts
