"""Evidence from the failure context (fl_tools context) for the selectors S6, S8a and S8b.

Everything here comes from the buggy version and the failing tests only: error output, stack frames, the test
code and coverage of the failing tests. Never the fix or the ground truth.
"""
import re
from typing import List, Optional

from ..context import method_key

NOISE_FRAME = re.compile(r"^(junit\.|org\.junit\.|sun\.|java\.|javax\.|jdk\.|org\.apache\.tools\.ant\.|"
                         r"org\.mockito\.internal\.creation|net\.sf\.cglib\.)")
MAX_TEST_CODE = 2000
MAX_OUTPUT_LINES = 12


def _tests(ctx: Optional[dict]) -> List[dict]:
    return (ctx or {}).get("tests") or []


def project_frames(test: dict, limit: int = 12) -> List[dict]:
    return [f for f in test.get("frames") or [] if not NOISE_FRAME.match(f["class"])][:limit]


def facts(ctx: Optional[dict], method_name: str) -> dict:
    """Per candidate: stack depth (None = not on any failing test's stack; overloads share a name), how many
    of the collected failing tests executed it, and the frame text."""
    tests = _tests(ctx)
    key = method_key(method_name)
    depth, frame = None, None
    for t in tests:
        for d, fr in enumerate(project_frames(t, limit=1000)):
            if fr["key"] == key and (depth is None or d < depth):
                depth, frame = d, f"{fr['class']}.{fr['method']}:{fr['line']}"
    entry = ((ctx or {}).get("methods") or {}).get(method_name) or {}
    covering = entry.get("failing_tests_covering")
    if covering is None:   # method id formats can differ slightly (generics): fall back to the name key
        covering = sum(1 for t in tests if any(method_key(m) == key for m in t.get("covered_methods") or []))
    return {"stack_depth": depth, "frame": frame, "covered_by": covering, "n_tests": len(tests)}


def evidence_lines(ctx: Optional[dict], method_name: str) -> str:
    f = facts(ctx, method_name)
    if not f["n_tests"]:
        return "Evidence: (no failure context)"
    stack = (f"on the stack trace of a failing test at depth {f['stack_depth']} ({f['frame']})"
             if f["stack_depth"] is not None else "not on the stack trace of any failing test")
    return f"Evidence: {stack}; executed by {f['covered_by']} of {f['n_tests']} failing tests."


def failure_block(ctx: Optional[dict], analysis: str = "", max_tests: int = 2) -> str:
    """The raw failure (test name, error, project frames, test code) followed by the pipeline's analysis."""
    parts = []
    for t in _tests(ctx)[:max_tests]:
        out = "\n".join(l for l in (t.get("output") or "").splitlines() if l.strip())
        head = (t.get("stack_trace") or [])[:2]
        frames = "\n".join(f"  at {f['class']}.{f['method']}:{f['line']}" for f in project_frames(t))
        code = ((t.get("test_method") or {}).get("code") or "").strip()
        parts.append(f"Failing test {t['name']}\n" + "\n".join(head[1:] if head and head[0].startswith("---") else head)
                     + (f"\nOutput:\n" + "\n".join(out.splitlines()[:MAX_OUTPUT_LINES]) if out else "")
                     + (f"\nStack (project frames):\n{frames}" if frames else "")
                     + (f"\nTest code:\n```java\n{code[:MAX_TEST_CODE]}\n```" if code else ""))
    text = "\n\n".join(parts)
    if analysis:
        text += ("\n\n" if text else "") + f"Analysis of the failure:\n{analysis}"
    return text or "(no failure information)"


def stack_key(ctx: Optional[dict], method_name: str) -> tuple:
    """Sort key for S6, larger = more suspicious: on the stack (shallower is better), then coverage share."""
    f = facts(ctx, method_name)
    on_stack = f["stack_depth"] is not None
    share = (f["covered_by"] or 0) / f["n_tests"] if f["n_tests"] else 0.0
    return (int(on_stack), -(f["stack_depth"] or 0) if on_stack else 0, share)
