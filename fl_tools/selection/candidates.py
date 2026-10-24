"""Load the stored candidate lists of a run, one case per attempted bug."""
from dataclasses import dataclass, field
from typing import List, Optional, Set

from ..funnel import classify
from ..results import BugRecord, load_records

INFRA = {"crashed", "not_run", "context_overflow"}


@dataclass
class BugCase:
    bug: str                    # e.g. "Lang-1"
    project: str
    stage: str                  # funnel stage of the source run (crashed, class_missed, top1, ...)
    truth: Set[str]             # ground-truth buggy methods (empty if unknown)
    candidates: List[dict] = field(default_factory=list)   # stored order = the source run's ranking
    record: Optional[BugRecord] = None

    @property
    def infra_failure(self) -> bool:
        return self.stage in INFRA

    @property
    def reachable(self) -> bool:
        """The buggy method is among the stored candidates (only then can a selector change anything)."""
        return any(c.get("method_name") in self.truth for c in self.candidates)


def load_cases(run_dir: str, soapfl_dir: Optional[str] = None) -> List[BugCase]:
    cases = []
    for record in load_records(run_dir, soapfl_dir):
        candidates = list((record.result or {}).get("buggy_methods", []))
        cases.append(BugCase(bug=record.bug.name, project=record.bug.project, stage=classify(record)["stage"],
                             truth=set(record.truth or []), candidates=candidates, record=record))
    return cases
