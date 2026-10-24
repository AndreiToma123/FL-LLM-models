"""Prompts of the judge selectors (written by us). Their hash goes into every selection run's metadata.

Only information the source run stored is shown: the bug-level failure analysis that the pipeline wrote
from the failing tests (`test_failure_causes`) and each candidate's class/method name, documentation and
code. No bug id, project name or ground truth. Package names are dropped from method names (they cannot be
removed from the code itself; a stated threat to validity).
"""
import hashlib
import re
from typing import List

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


def _method_block(label: str, c: dict) -> str:
    code = re.sub(r"^```\w*\n?|```$", "", (c.get("method_code") or "").strip()).strip()
    doc = _clip(c.get("method_doc") or "", MAX_DOC_CHARS)
    return (f"Method {label}: {short_name(c.get('method_name', ''))}\n"
            + (f"Documentation: {doc}\n" if doc else "")
            + f"```java\n{_clip(code, MAX_CODE_CHARS)}\n```")


def pairwise(failure: str, a: dict, b: dict) -> List[dict]:
    user = ("A test suite fails because of a single bug in the production code.\n\n"
            f"Analysis of the failure:\n{failure}\n\n"
            f"{_method_block('A', a)}\n\n{_method_block('B', b)}\n\n"
            "Which method is more likely to contain the bug that has to be fixed to make the tests pass? "
            "Answer with exactly one letter: A or B.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def pointwise(failure: str, c: dict) -> List[dict]:
    user = ("A test suite fails because of a single bug in the production code.\n\n"
            f"Analysis of the failure:\n{failure}\n\n"
            f"{_method_block('M', c)}\n\n"
            "How likely is it that method M contains the bug that has to be fixed to make the tests pass? "
            "Answer with a single digit from 0 (certainly not) to 9 (certainly).")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_choice(text: str):
    """'A' or 'B' from the answer, or None."""
    m = re.search(r"\b([AB])\b", (text or "").strip().upper())
    return m.group(1) if m else None


def version() -> str:
    probe = {"x": "y"}
    material = SYSTEM + str(pairwise("F", dict(probe), dict(probe))) + str(pointwise("F", dict(probe))) + \
        f"{MAX_FAILURE_CHARS}/{MAX_CODE_CHARS}/{MAX_DOC_CHARS}"
    return hashlib.sha256(material.encode()).hexdigest()[:12]
