"""Selectors: take a bug's stored candidate list, return a new full order (and what they did).

Every selector only reorders methods INSIDE a group of equal sort keys (the source run's ties); groups keep
their order. So a selector can never move a method above one the source run scored higher; it decides the
ties. Model-based selectors (log-prob score, listwise, pairwise) will be added here with the same interface.
"""
import hashlib
import random
from typing import Callable, Dict, List, Tuple

from ..ties import _groups
from . import features as feat
from .candidates import BugCase


def _bug_rng(seed: int, bug: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{bug}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


class Selector:
    name = "base"
    description = ""
    model_calls = False

    def order(self, case: BugCase, seed: int = 0) -> Tuple[List[dict], dict]:
        raise NotImplementedError


class S0(Selector):
    name = "S0"
    description = "source run's own order (ties in review order)"

    def order(self, case, seed=0):
        return list(case.candidates), {}


class S0r(Selector):
    name = "S0r"
    description = "random order inside ties (one seeded draw; the expectation is reported separately)"

    def order(self, case, seed=0):
        rng = _bug_rng(seed, case.bug)
        out = []
        for g in _groups(case.candidates):
            g = list(g)
            rng.shuffle(g)
            out += g
        return out, {"seed": seed}


class FeatureTieBreak(Selector):
    """Sort each tie group by a feature key (descending), stable: equal keys keep review order."""
    key: Callable[[dict], tuple] = None

    def order(self, case, seed=0):
        fs = feat.compute(case.candidates)
        feats = {id(c): f for c, f in zip(case.candidates, fs)}
        out = []
        for g in _groups(case.candidates):
            out += sorted(g, key=lambda c: self.key(feats[id(c)]), reverse=True)
        return out, {"features": {c["method_name"]: feats[id(c)] for c in case.candidates}}


class S1(FeatureTieBreak):
    name = "S1"
    description = "ties broken by lexical evidence: method named in the failure analysis, then name overlap, " \
                  "then TF-IDF similarity of the method to the failure analysis"

    @staticmethod
    def key(f):
        return (f["mentioned"], f["name_overlap"], f["body_similarity"])


class S1body(FeatureTieBreak):
    name = "S1-body"
    description = "ties broken by TF-IDF similarity of the method (name, doc, code) to the failure analysis only"

    @staticmethod
    def key(f):
        return (f["body_similarity"],)


REGISTRY: Dict[str, Selector] = {s.name: s for s in (S0(), S0r(), S1(), S1body())}


def get(name: str) -> Selector:
    if name not in REGISTRY:
        raise KeyError(f"unknown selector {name!r}; known: {', '.join(REGISTRY)}")
    return REGISTRY[name]
