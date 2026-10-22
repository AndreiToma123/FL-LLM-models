"""Pure logic of our HypoDeduce re-implementation (no SoapFL imports, unit-tested).

Parsing of model answers, the retention rule (union over hypotheses), hypothesis
selection and the final ranking. Everything here is OUR design where the paper
(Le, Zheng, Kang, ICSE-NIER 2026) does not specify the mechanism; see
docs/HYPODEDUCE.md for which parts come from the paper and which are ours.
"""
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# ----------------------------------------------------------------------------- parsing

_HYP_HEADER = re.compile(
    r"^[ \t>*#_-]*(?:\*\*)?\s*hypothesis\s*(?:#\s*)?(\d+)\s*(?:\*\*)?\s*[:.)\]-]?\s*(?:\*\*)?\s*",
    re.IGNORECASE | re.MULTILINE)
_NUMBERED = re.compile(r"^[ \t]*(?:\*\*)?(\d+)[.)]\s+(?:\*\*)?", re.MULTILINE)


def _split_on(pattern: re.Pattern, text: str) -> List[Tuple[int, str]]:
    matches = list(pattern.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip().strip("*").strip()
        if body:
            out.append((int(m.group(1)), body))
    return out


def parse_hypotheses(text: str, limit: int) -> List[str]:
    """Split the hypothesis-generation answer into at most `limit` hypothesis texts.

    Accepts "Hypothesis 1: ...", "**Hypothesis 1** - ...", and plain numbered lists "1. ...".
    Duplicates (same text after whitespace normalisation) are dropped. Returns [] if nothing parses.
    """
    text = (text or "").strip()
    parts = _split_on(_HYP_HEADER, text) or _split_on(_NUMBERED, text)
    seen, out = set(), []
    for _, body in parts:
        key = " ".join(body.lower().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(body)
        if len(out) >= limit:
            break
    return out


_POUND = re.compile(r"#\s*((?:[\w$]+\.)+[\w$]+)\s*#")
_DOTTED = re.compile(r"(?:\w+\.)+[\w$]+")


def parse_ranked_classes(text: str, known: Iterable[str], limit: int) -> List[str]:
    """Classes named in the answer, in the order the model gave them, restricted to `known`.

    Names marked with pound signs (#a.b.C#) come first, as the prompt asks; other dotted names that
    are covered classes are used as a fallback. At most `limit` classes.
    """
    known = set(known)
    ordered: List[str] = []
    for pattern in (_POUND, _DOTTED):
        for m in pattern.finditer(text or ""):
            name = m.group(1) if pattern is _POUND else m.group(0)
            if name in known and name not in ordered:
                ordered.append(name)
    return ordered[:limit] if limit > 0 else ordered


# ----------------------------------------------------------------------------- retention

def retain(per_hypothesis: Dict[int, Dict[str, List[str]]]) -> Tuple[Dict[str, List[str]], Dict[str, List[int]]]:
    """Retention rule of the paper: an element stays if at least ONE hypothesis keeps it.

    per_hypothesis: {hypothesis index: {class: [methods kept for that hypothesis]}}
    Returns (class -> union of methods, in first-seen order) and (method -> supporting hypotheses).
    """
    union: Dict[str, List[str]] = {}
    support: Dict[str, List[int]] = {}
    for k in sorted(per_hypothesis):
        for cls, methods in per_hypothesis[k].items():
            bucket = union.setdefault(cls, [])
            for m in methods:
                if m not in bucket:
                    bucket.append(m)
                if k not in support.setdefault(m, []):
                    support[m].append(k)
    return union, support


# ----------------------------------------------------------------------------- selection

SELECTION_RULES = ("max", "mean_top3")


def plausibility(scores: Sequence[float], rule: str = "max") -> Tuple[float, float]:
    """Plausibility of one hypothesis from the scores of the methods it supports (our rule).

    Returns a sort key (primary, secondary). "max": best method score, then mean of the top 3;
    "mean_top3": mean of the top 3, then best. A hypothesis that kept no method scores (-1, -1).
    """
    if not scores:
        return (-1.0, -1.0)
    ordered = sorted(scores, reverse=True)
    best, top3 = ordered[0], sum(ordered[:3]) / len(ordered[:3])
    if rule == "max":
        return (best, top3)
    if rule == "mean_top3":
        return (top3, best)
    raise ValueError(f"unknown selection rule {rule!r}; use one of {SELECTION_RULES}")


def select_hypothesis(n_hypotheses: int, scores: Dict[Tuple[str, int], float],
                      rule: str = "max") -> Tuple[Optional[int], Dict[int, Tuple[float, float]]]:
    """Pick the most plausible hypothesis. Ties go to the earlier hypothesis (the model's own order).

    scores: {(method, hypothesis index): score}. Returns (selected index or None, plausibility per index).
    """
    plaus = {k: plausibility([s for (m, h), s in scores.items() if h == k], rule) for k in range(n_hypotheses)}
    if not plaus or max(plaus.values()) == (-1.0, -1.0):
        return None, plaus
    best = max(plaus.values())
    selected = min(k for k, v in plaus.items() if v == best)
    return selected, plaus


def rank_key(method: str, selected: Optional[int], support: Dict[str, List[int]],
             scores: Dict[Tuple[str, int], float]) -> Tuple[int, float]:
    """Sort key of a method in the final list (our rule; higher is more suspicious).

    Methods supported by the selected hypothesis come first, ranked by their score under it; the other
    retained methods follow, ranked by their best score under any hypothesis. Within equal keys the
    original order (review order) is kept by the stable sort, as in SoapFL.
    """
    hyps = support.get(method, [])
    if selected is not None and selected in hyps and (method, selected) in scores:
        return (1, float(scores[(method, selected)]))
    own = [scores[(method, k)] for k in hyps if (method, k) in scores]
    return (0, float(max(own)) if own else 0.0)


def final_order(methods: Sequence[str], selected: Optional[int], support: Dict[str, List[int]],
                scores: Dict[Tuple[str, int], float]) -> List[Tuple[str, Tuple[int, float]]]:
    keyed = [(m, rank_key(m, selected, support, scores)) for m in methods]
    return sorted(keyed, key=lambda item: item[1], reverse=True)   # stable: ties keep review order
