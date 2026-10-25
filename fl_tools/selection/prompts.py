"""Prompts of the judge selectors (written by us). Their hash goes into every selection run's metadata.

Only information the source run stored is shown: the bug-level failure analysis that the pipeline wrote
from the failing tests (`test_failure_causes`) and each candidate's class/method name, documentation and
code. No bug id, project name or ground truth. Package names are dropped from method names (they cannot be
removed from the code itself; a stated threat to validity).
"""
import hashlib
import re
from typing import List, Optional

SYSTEM = ("You are an experienced Java developer who locates the source of failing tests. "
          "Answer exactly in the requested format, without explanation.")

MAX_FAILURE_CHARS = 3000
MAX_CODE_CHARS = 2500
MAX_DOC_CHARS = 400


def short_name(method_name: str) -> str:
    """'org.a.b.Foo$Bar::baz(int)' -> 'Foo$Bar::baz(int)' (drop the package)."""
    cls, _, rest = method_name.partition("::")
    return f"{cls.split('.')[-1]}::{rest}" if rest else method_name.split(".")[-1]


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "\n... (truncated)"


def failure_text(candidates: List[dict]) -> str:
    """The distinct failure analyses of the shortlisted candidates (usually one), clipped."""
    seen = []
    for c in candidates:
        t = (c.get("test_failure_causes") or "").strip()
        if t and t not in seen:
            seen.append(t)
    joined = "\n\n".join(seen[:2]) or "(no failure analysis stored)"
    return _clip(joined, MAX_FAILURE_CHARS)


def _method_block(label: str, c: dict, evidence: Optional[str] = None) -> str:
    code = re.sub(r"^```\w*\n?|```$", "", (c.get("method_code") or "").strip()).strip()
    doc = _clip(c.get("method_doc") or "", MAX_DOC_CHARS)
    return (f"Method {label}: {short_name(c.get('method_name', ''))}\n"
            + (f"Documentation: {doc}\n" if doc else "")
            + (f"{evidence}\n" if evidence else "")
            + f"```java\n{_clip(code, MAX_CODE_CHARS)}\n```")


def _failure_heading(failure: str, raw: bool) -> str:
    # raw=True: `failure` already holds the failing tests, stack and analysis (evidence selectors)
    return f"{failure}" if raw else f"Analysis of the failure:\n{failure}"


def pairwise(failure: str, a: dict, b: dict, ev_a: Optional[str] = None, ev_b: Optional[str] = None) -> List[dict]:
    raw = ev_a is not None or ev_b is not None
    user = ("A test suite fails because of a single bug in the production code.\n\n"
            f"{_failure_heading(failure, raw)}\n\n"
            f"{_method_block('A', a, ev_a)}\n\n{_method_block('B', b, ev_b)}\n\n"
            "Which method is more likely to contain the bug that has to be fixed to make the tests pass? "
            "Answer with exactly one letter: A or B.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def pointwise(failure: str, c: dict, evidence: Optional[str] = None) -> List[dict]:
    user = ("A test suite fails because of a single bug in the production code.\n\n"
            f"{_failure_heading(failure, evidence is not None)}\n\n"
            f"{_method_block('M', c, evidence)}\n\n"
            "How likely is it that method M contains the bug that has to be fixed to make the tests pass? "
            "Answer with a single digit from 0 (certainly not) to 9 (certainly).")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_choice(text: str):
    """'A' or 'B' from the answer, or None."""
    m = re.search(r"\b([AB])\b", (text or "").strip().upper())
    return m.group(1) if m else None


def version(evidence: bool = False) -> str:
    probe = {"x": "y"}
    ev = "E" if evidence else None
    material = SYSTEM + str(pairwise("F", dict(probe), dict(probe), ev, ev)) + str(pointwise("F", dict(probe), ev)) + \
        f"{MAX_FAILURE_CHARS}/{MAX_CODE_CHARS}/{MAX_DOC_CHARS}"
    if evidence:
        from . import evidence as evm
        import inspect
        material += inspect.getsource(evm)
    return hashlib.sha256(material.encode()).hexdigest()[:12]
