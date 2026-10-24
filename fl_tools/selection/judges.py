"""Model-based selectors (they make new model calls, cached by the client).

S5     pairwise: every pair of shortlisted candidates is shown to the model in BOTH orders ("A or B?"); a pair
       counts as a win only if both answers agree, otherwise it is a draw (this cancels position bias).
       Candidates are ranked by Copeland score (wins - losses). Remaining ties keep the source order.
S2     log-prob expected score: one call per shortlisted candidate asks for a single digit 0-9; the expected
       value over the digit tokens' probabilities gives a continuous score (no more saturated 8s). Needs an
       endpoint that returns token log-probabilities.
S5+S2  pairwise first; candidates still tied on Copeland score are ordered by the S2 expected score (computed
       only for those candidates).

Shortlist (which candidates the judge sees, at most K, default 8):
  top-tie  the group of candidates that share the source run's best sort key (SoapFL: the top score). Only
           this group decides Top-1; below it the source order is kept.
  top-k    the K best candidates by their raw score, ignoring HypoDeduce's hypothesis tiers (for HypoDeduce
           lists, where the buggy method is often below the selected hypothesis's tier).
"""
import math
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from ..ties import _groups
from . import prompts
from .candidates import BugCase
from .llm import JudgeClient, JudgeError
from .selectors import REGISTRY, Selector

SHORTLISTS = ("top-tie", "top-k")


def raw_score(c: dict) -> float:
    by_h = c.get("scores_by_hypothesis")
    if by_h:
        return float(max(by_h.values()))
    return float(c.get("score") or 0)


def shortlist(candidates: List[dict], mode: str, k: int) -> Tuple[List[int], List[int]]:
    """(indices judged, indices kept below in source order)."""
    n = len(candidates)
    if mode == "top-tie":
        groups = _groups(candidates)
        head = list(range(len(groups[0]))) if groups and len(groups[0]) > 1 else []
    elif mode == "top-k":
        order = sorted(range(n), key=lambda i: -raw_score(candidates[i]))   # stable: source order on ties
        head = order[:k] if n > 1 else []
    else:
        raise ValueError(f"unknown shortlist {mode!r}; use one of {SHORTLISTS}")
    head = sorted(head[:k]) if mode == "top-tie" else head[:k]
    rest = [i for i in range(n) if i not in set(head)]
    return head, rest


class JudgeSelector(Selector):
    model_calls = True

    def __init__(self):
        self.client: Optional[JudgeClient] = None
        self.k, self.mode = 8, "top-tie"

    def configure(self, client: JudgeClient, k: int = 8, mode: str = "top-tie"):
        self.client, self.k, self.mode = client, k, mode
        return self

    # ------------------------------------------------------------------ pieces
    def _expected(self, failure: str, c: dict, seed: int, log: dict) -> float:
        r = self.client.chat(prompts.pointwise(failure, c), max_tokens=1, seed=seed, logprobs=True, top_logprobs=20)
        self._count(r, log)
        if not r["top_logprobs"]:
            raise JudgeError("the endpoint returned no log-probabilities, so S2 cannot run here. Ollama returns them "
                             "only in recent versions (reported >= 0.12, unverified); vLLM on CSC returns them. "
                             "Check with: python -m fl_tools select --check-logprobs")
        probs: Dict[int, float] = {}
        for tok, lp in r["top_logprobs"]:
            t = tok.strip()
            if len(t) == 1 and t.isdigit():
                probs[int(t)] = probs.get(int(t), 0.0) + math.exp(lp)
        if not probs:
            log.setdefault("no_digit_logprobs", 0)
            log["no_digit_logprobs"] += 1
            digits = [ch for ch in r["text"] if ch.isdigit()]
            return float(digits[0]) if digits else 0.0
        total = sum(probs.values())
        return sum(d * p for d, p in probs.items()) / total

    def _pairwise(self, failure: str, cands: List[dict], seed: int, log: dict) -> Dict[int, int]:
        score = {i: 0 for i in range(len(cands))}
        draws = inconsistent = 0
        for i, j in combinations(range(len(cands)), 2):
            r1 = self.client.chat(prompts.pairwise(failure, cands[i], cands[j]), max_tokens=2, seed=seed)
            r2 = self.client.chat(prompts.pairwise(failure, cands[j], cands[i]), max_tokens=2, seed=seed)
            self._count(r1, log)
            self._count(r2, log)
            c1, c2 = prompts.parse_choice(r1["text"]), prompts.parse_choice(r2["text"])
            w1 = {"A": i, "B": j}.get(c1)
            w2 = {"A": j, "B": i}.get(c2)
            if w1 is not None and w1 == w2:
                score[w1] += 1
                score[j if w1 == i else i] -= 1
            else:
                draws += 1
                inconsistent += int(w1 is not None and w2 is not None)   # both answered, but disagreed
        log["pairs"] = log.get("pairs", 0) + len(cands) * (len(cands) - 1) // 2
        log["draws"] = log.get("draws", 0) + draws
        log["position_inconsistent"] = log.get("position_inconsistent", 0) + inconsistent
        return score

    @staticmethod
    def _count(r: dict, log: dict) -> None:
        log["calls"] = log.get("calls", 0) + (0 if r.get("cached") else 1)
        log["cached_calls"] = log.get("cached_calls", 0) + (1 if r.get("cached") else 0)
        log["tokens"] = log.get("tokens", 0) + (r.get("prompt_tokens") or 0) + (r.get("completion_tokens") or 0)
        log["seconds"] = round(log.get("seconds", 0.0) + (0.0 if r.get("cached") else r.get("seconds", 0.0)), 3)

    def judge(self, cands: List[dict], failure: str, seed: int, log: dict) -> List[int]:
        raise NotImplementedError

    def order(self, case: BugCase, seed: int = 0):
        if self.client is None:
            raise JudgeError(f"selector {self.name} needs a model: run it through `fl_tools select` with an endpoint")
        cands = case.candidates
        head, rest = shortlist(cands, self.mode, self.k)
        log = {"shortlist": [cands[i]["method_name"] for i in head], "mode": self.mode, "k": self.k}
        if len(head) < 2:
            return list(cands), dict(log, calls=0)
        sub = [cands[i] for i in head]
        new = self.judge(sub, prompts.failure_text(sub), seed, log)
        return [sub[i] for i in new] + [cands[i] for i in rest], log


class S5(JudgeSelector):
    name = "S5"
    description = "pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order"

    def judge(self, cands, failure, seed, log):
        score = self._pairwise(failure, cands, seed, log)
        log["copeland"] = {cands[i]["method_name"]: s for i, s in score.items()}
        return sorted(range(len(cands)), key=lambda i: -score[i])


class S2(JudgeSelector):
    name = "S2"
    description = "expected 0-9 score from the judge's digit log-probabilities on the shortlist"

    def judge(self, cands, failure, seed, log):
        exp = [self._expected(failure, c, seed, log) for c in cands]
        log["expected_score"] = {c["method_name"]: round(e, 4) for c, e in zip(cands, exp)}
        return sorted(range(len(cands)), key=lambda i: -exp[i])


class S5S2(JudgeSelector):
    name = "S5+S2"
    description = "pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score"

    def judge(self, cands, failure, seed, log):
        score = self._pairwise(failure, cands, seed, log)
        log["copeland"] = {cands[i]["method_name"]: s for i, s in score.items()}
        exp: Dict[int, float] = {}
        by_score: Dict[int, List[int]] = {}
        for i, s in score.items():
            by_score.setdefault(s, []).append(i)
        for members in by_score.values():
            if len(members) > 1:                 # S2 only where pairwise left a tie
                for i in members:
                    exp[i] = self._expected(failure, cands[i], seed, log)
        log["expected_score"] = {cands[i]["method_name"]: round(e, 4) for i, e in exp.items()}
        return sorted(range(len(cands)), key=lambda i: (-score[i], -exp.get(i, 0.0)))


for _sel in (S5(), S2(), S5S2()):
    REGISTRY[_sel.name] = _sel
