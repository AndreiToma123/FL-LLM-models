"""Cheap, deterministic, ground-truth-free features of a candidate method (no model calls).

Only text that the source run stored is used: the candidate's own fields (method name, class name, doc,
code) and the bug-level failure analysis that the pipeline produced before ranking (`test_failure_causes`,
written by the model from the failing test, stack trace and test output). The model's per-method
justification (`reason`) and its score are NOT used here: they are the signal being re-judged.
"""
import math
import re
from collections import Counter
from typing import Dict, List

_SPLIT_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
_WORDS = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STOP = set("""
a an the and or not of to in on for with by is are was were be been it its this that these those as at from
if else then than when while do does did can could should would will may might must shall into out over under
public private protected static final void return new null true false class interface extends implements
int long short byte char float double boolean string object get set test tests method methods value values
code line lines java org com junit assert assertion expected actual error exception failed failure fail
""".split())


def tokens(text: str) -> List[str]:
    """Identifier-aware tokens: camelCase and snake_case are split, lower-cased, stop words and 1-2 letters dropped."""
    out = []
    for word in _WORDS.findall(text or ""):
        for part in word.split("_"):
            for piece in _SPLIT_CAMEL.findall(part):
                piece = piece.lower()
                if len(piece) > 2 and piece not in STOP:
                    out.append(piece)
    return out


def method_simple_name(method_name: str) -> str:
    """'a.b.C$D::foo(int)' -> 'foo'."""
    after = method_name.split("::")[-1]
    return after.split("(")[0]


def class_simple_name(method_name: str) -> str:
    """'a.b.C$D::foo(int)' -> 'D' (innermost class)."""
    cls = method_name.split("::")[0]
    return re.split(r"[.$]", cls)[-1]


def failure_text(candidate: dict) -> str:
    return candidate.get("test_failure_causes") or ""


def name_overlap(candidate: dict) -> float:
    """Share of the method's simple-name tokens that occur in the failure analysis (0..1)."""
    name = tokens(method_simple_name(candidate.get("method_name", "")))
    if not name:
        return 0.0
    fail = set(tokens(failure_text(candidate)))
    return sum(1 for t in name if t in fail) / len(name)


def mentioned(candidate: dict) -> float:
    """1 if the failure analysis names the method literally (e.g. 'Foo.bar' or 'bar('), else 0."""
    text = failure_text(candidate)
    name = method_simple_name(candidate.get("method_name", ""))
    if not name or name in ("<init>",):
        return 0.0
    cls = class_simple_name(candidate.get("method_name", ""))
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*\(|{re.escape(cls)}\s*[.#]\s*{re.escape(name)}(?![A-Za-z0-9_])"
    return 1.0 if re.search(pattern, text) else 0.0


def body_similarity(candidate: dict, idf: Dict[str, float]) -> float:
    """TF-IDF cosine between the method (name, doc, code) and the failure analysis."""
    doc = Counter(tokens(" ".join([candidate.get("method_name", ""), candidate.get("method_doc", "") or "",
                                   candidate.get("method_code", "") or ""])))
    fail = Counter(tokens(failure_text(candidate)))
    if not doc or not fail:
        return 0.0
    def vec(c):
        return {t: n * idf.get(t, 1.0) for t, n in c.items()}
    a, b = vec(doc), vec(fail)
    dot = sum(v * b.get(t, 0.0) for t, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def idf_for(candidates: List[dict]) -> Dict[str, float]:
    """IDF over the candidates of ONE bug (terms shared by all candidates carry little information)."""
    docs = [set(tokens(" ".join([c.get("method_name", ""), c.get("method_doc", "") or "",
                                  c.get("method_code", "") or ""]))) for c in candidates]
    n = len(docs) or 1
    df = Counter(t for d in docs for t in d)
    return {t: math.log((1 + n) / (1 + k)) + 1.0 for t, k in df.items()}


def compute(candidates: List[dict]) -> List[dict]:
    """Feature dict per candidate, in the same order."""
    idf = idf_for(candidates)
    return [{"mentioned": mentioned(c), "name_overlap": round(name_overlap(c), 4),
             "body_similarity": round(body_similarity(c, idf), 4),
             "code_lines": len((c.get("method_code") or "").splitlines())} for c in candidates]
