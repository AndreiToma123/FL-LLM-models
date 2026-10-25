"""S8b: agentic investigator. The model chooses which evidence to look at (tool calls over the FROZEN failure
context and the stored candidates), up to a step cap, then submits a ranking of the shortlisted candidates.

* Tools are read-only and answer from files (failure context, result.json), so a run is deterministic at
  temperature 0 and every turn is cached: replays and the later test reveal repeat no call.
* Position bias: the investigation runs twice, once with the candidates in source order and once reversed
  (labels C1..Cn reassigned each time); the two rankings are combined by mean position (Borda). Whether the
  two runs agree on the top candidate is logged (a confidence signal for the gated escalation, B).
* Protocols: "native" = OpenAI tool calls (Ollama/vLLM `tools`); "json" = the model writes one JSON action
  per turn ({"tool": ..., "args": {...}}), for endpoints without tool calling. Choose with --agent-protocol.
* Nothing from the fix, VCS history or ground truth is reachable; the source run's score and reason are not
  shown either.
"""
import json
import re
from typing import Dict, List, Optional, Tuple

from . import evidence as ev
from . import prompts
from .judges import JudgeSelector

MAX_TOOL_CHARS = 3000
MAX_CONVERSATION_CHARS = 36000     # keeps the conversation inside a 16k-token context (about 4 chars per token)
TURN_TOKENS = 400

TOOL_SPECS = [
    ("list_failing_tests", "List the failing tests with their first error line.", {}),
    ("get_test", "Source code of a failing test method and its error output.",
     {"index": ("integer", "test number from list_failing_tests, starting at 1")}),
    ("get_stack_trace", "Project frames of a failing test's stack trace (top frame first).",
     {"index": ("integer", "test number from list_failing_tests, starting at 1")}),
    ("get_candidate", "Source code and documentation of a candidate method.",
     {"label": ("string", "candidate label, e.g. C1")}),
    ("get_coverage", "Whether a candidate is on a failing test's stack (depth) and how many failing tests "
                     "executed it.", {"label": ("string", "candidate label, e.g. C1")}),
    ("search_methods", "Find methods executed by the failing tests whose name contains a text.",
     {"query": ("string", "part of a class or method name")}),
    ("get_method_code", "Source code of any method executed by the failing tests (when available).",
     {"method": ("string", "Class::method as shown by search_methods")}),
    ("submit_ranking", "Finish: rank ALL candidates, most likely buggy first.",
     {"ranking": ("array", "candidate labels, e.g. [\"C2\", \"C1\", \"C3\"]"),
      "reason": ("string", "one sentence")}),
]

SYSTEM = ("You are an experienced Java developer who locates the source of failing tests. You investigate with "
          "the tools, then call submit_ranking. Be efficient: at most {steps} tool calls before submitting.")
JSON_RULES = ("\n\nAnswer EVERY turn with exactly one JSON object and nothing else, for example "
              '{"tool": "get_coverage", "args": {"label": "C1"}} or '
              '{"tool": "submit_ranking", "args": {"ranking": ["C2", "C1"], "reason": "..."}}.\nTools:\n')


def tool_schemas() -> List[dict]:
    out = []
    for name, desc, params in TOOL_SPECS:
        props = {}
        for p, (typ, d) in params.items():
            props[p] = {"type": typ, "description": d}
            if typ == "array":
                props[p]["items"] = {"type": "string"}
        req = [p for p in params if p != "reason"]
        out.append({"type": "function", "function": {"name": name, "description": desc,
                                                      "parameters": {"type": "object", "properties": props,
                                                                     "required": req}}})
    return out


def _clip(text: str, n: int = MAX_TOOL_CHARS) -> str:
    return text if len(text) <= n else text[:n] + "\n... (truncated)"


class Tools:
    """Answers tool calls from the frozen failure context and the shortlisted candidates."""

    def __init__(self, ctx: Optional[dict], labelled: Dict[str, dict]):
        self.ctx, self.labelled = ctx or {}, labelled
        self.tests = self.ctx.get("tests") or []

    def _test(self, args) -> Optional[dict]:
        try:
            i = int(args.get("index", 1))
        except (TypeError, ValueError):
            return None
        return self.tests[i - 1] if 1 <= i <= len(self.tests) else None

    def _cand(self, args) -> Optional[dict]:
        label = str(args.get("label", "")).strip().upper()
        return self.labelled.get(label)

    def call(self, name: str, args: dict) -> Tuple[str, bool]:
        """(answer, valid)."""
        args = args if isinstance(args, dict) else {}
        if name == "list_failing_tests":
            if not self.tests:
                return "No failing-test details available.", True
            rows = []
            for i, t in enumerate(self.tests, 1):
                first = next((l for l in (t.get("stack_trace") or [])[1:2]), "") or (t.get("output") or "").strip()[:200]
                rows.append(f"{i}. {t['name']}: {first}")
            total = self.ctx.get("failing_tests_total", len(self.tests))
            return "\n".join(rows) + (f"\n({total} failing tests in total; {len(self.tests)} shown)"
                                      if total > len(self.tests) else ""), True
        if name == "get_test":
            t = self._test(args)
            if t is None:
                return f"No such test. Use 1 to {len(self.tests)}.", False
            code = ((t.get("test_method") or {}).get("code") or "(test code not available)").strip()
            out = (t.get("output") or "").strip()
            return _clip(f"{t['name']}\n```java\n{code}\n```\nOutput:\n{out}"), True
        if name == "get_stack_trace":
            t = self._test(args)
            if t is None:
                return f"No such test. Use 1 to {len(self.tests)}.", False
            head = (t.get("stack_trace") or [])[1:2]
            frames = [f"{d}. {f['class']}.{f['method']}:{f['line']}" for d, f in enumerate(ev.project_frames(t, 30))]
            return _clip("\n".join(head + frames) or "(no project frames)"), True
        if name in ("get_candidate", "get_coverage"):
            c = self._cand(args)
            if c is None:
                return f"No such candidate. Use one of {', '.join(self.labelled)}.", False
            if name == "get_candidate":
                code = re.sub(r"^```\w*\n?|```$", "", (c.get("method_code") or "").strip()).strip()
                doc = (c.get("method_doc") or "").strip()
                return _clip(f"{prompts.short_name(c['method_name'])}\n" + (f"Documentation: {doc}\n" if doc else "")
                             + f"```java\n{code}\n```"), True
            label = str(args.get("label", "")).strip().upper()
            return (f"{label} {prompts.short_name(c['method_name'])}: "
                    + ev.evidence_lines(self.ctx, c["method_name"]).replace("Evidence: ", "")), True
        if name == "search_methods":
            q = str(args.get("query", "")).strip().lower()
            if len(q) < 2:
                return "Query too short.", False
            hits = []
            for m, e in sorted((self.ctx.get("methods") or {}).items()):
                if q in m.lower():
                    depth = e.get("stack_depth")
                    hits.append(f"{prompts.short_name(m)} (executed by {e.get('failing_tests_covering')} failing tests"
                                + (f", stack depth {depth}" if depth is not None else "") + ")")
            return (_clip("\n".join(hits[:15]) + (f"\n... {len(hits) - 15} more" if len(hits) > 15 else ""))
                    if hits else "No executed method matches."), True
        if name == "get_method_code":
            want = str(args.get("method", "")).strip()
            for label, c in self.labelled.items():
                if want and (want in (c["method_name"], prompts.short_name(c["method_name"])) or want == label):
                    return self.call("get_candidate", {"label": label})
            for m, body in (self.ctx.get("method_code") or {}).items():
                if want and (want == m or want == prompts.short_name(m) or
                             prompts.short_name(m).split("(")[0] == want.split("(")[0]):
                    return _clip(f"{prompts.short_name(m)}\n```java\n{body.get('code', '')}\n```"), True
            return "Code not available for that method (only methods executed by the failing tests in the " \
                   "relevant classes are stored).", False
        return f"Unknown tool {name!r}.", False


def parse_ranking(value, labels: List[str]) -> Optional[List[str]]:
    """Accept a list of labels or text like 'C2 > C1, C3'; keep the first mention; append missing labels."""
    if isinstance(value, str):
        found = re.findall(r"\bC\d+\b", value.upper())
    elif isinstance(value, list):
        found = [str(v).strip().upper() for v in value]
    else:
        return None
    seen = []
    for f in found:
        if f in labels and f not in seen:
            seen.append(f)
    if not seen:
        return None
    return seen + [l for l in labels if l not in seen]


TOOL_NAMES = {n for n, _, _ in TOOL_SPECS}


def _action_from(obj) -> Optional[Tuple[str, dict]]:
    """{"tool": n, "args": {}} (our JSON protocol), {"name": n, "arguments": {} or "json"} (Qwen/Hermes-style
    tool call written as text), {"function": {"name", "arguments"}} (OpenAI-style object as text)."""
    if isinstance(obj, list):
        for item in obj:
            got = _action_from(item)
            if got:
                return got
        return None
    if not isinstance(obj, dict):
        return None
    if isinstance(obj.get("function"), dict):
        return _action_from(obj["function"])
    name = obj.get("tool") or obj.get("name") or obj.get("tool_name")
    if not isinstance(name, str) or name not in TOOL_NAMES:
        return None
    args = obj.get("args", obj.get("arguments", obj.get("parameters", {})))
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            args = {}
    return name, args if isinstance(args, dict) else {}


def parse_json_action(text: str) -> Optional[Tuple[str, dict]]:
    """First tool action written as JSON anywhere in the text (also inside <tool_call> tags or code fences)."""
    text = text or ""
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        got = _action_from(obj)
        if got:
            return got
    return None


class S8b(JudgeSelector):
    name = "S8b"
    uses_evidence = True
    description = ("agentic investigator: tool calls over the failure context and the candidates (step cap), "
                   "then a ranking; run forward and reversed, combined by mean position")

    def __init__(self):
        super().__init__()
        self.max_steps, self.protocol = 6, "native"

    def configure(self, client, k: int = 8, mode: str = "top-tie", max_steps: int = 6, protocol: str = "native"):
        super().configure(client, k, mode)
        self.max_steps, self.protocol = max_steps, protocol
        return self

    # ------------------------------------------------------------------ one investigation
    def _intro(self, ctx, analysis: str, labels: List[str], labelled: Dict[str, dict]) -> str:
        cands = "\n".join(f"{l}: {prompts.short_name(labelled[l]['method_name'])}" for l in labels)
        tests = ctx.get("tests") or []
        first = tests[0] if tests else {}
        err = next((l for l in (first.get("stack_trace") or [])[1:2]), "")
        top = ", ".join(f"{f['class'].split('.')[-1]}.{f['method']}" for f in ev.project_frames(first, 4))
        return ("A test suite fails because of a single bug in the production code. One of the candidate methods "
                "below most likely contains it.\n\n"
                f"First failing test: {first.get('name', '?')} ({len(tests)} collected)\nError: {err}\n"
                + (f"Top project frames: {top}\n" if top else "")
                + (f"\nAnalysis of the failure (written earlier by another assistant):\n{analysis}\n" if analysis else "")
                + f"\nCandidates:\n{cands}\n\nInvestigate with the tools, then call submit_ranking with all "
                  f"{len(labels)} candidates, most likely buggy first.")

    def _investigate(self, ctx, analysis: str, ordered: List[dict], seed: int, log: dict) -> Optional[List[int]]:
        labels = [f"C{i + 1}" for i in range(len(ordered))]
        labelled = dict(zip(labels, ordered))
        tools = Tools(ctx, labelled)
        native = self.protocol == "native"
        system = SYSTEM.format(steps=self.max_steps)
        if not native:
            system += JSON_RULES + "\n".join(
                f"- {n}({', '.join(p)}): {d}" for n, d, p in ((n, d, list(p)) for n, d, p in TOOL_SPECS))
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": self._intro(ctx, analysis, labels, labelled)}]
        schemas = tool_schemas()
        submit_only = [s for s in schemas if s["function"]["name"] == "submit_ranking"]
        tool_steps = run_invalid = 0
        for turn in range(self.max_steps + 3):
            forced = (tool_steps >= self.max_steps or run_invalid >= 2
                      or sum(len(str(m.get("content", ""))) for m in messages) > MAX_CONVERSATION_CHARS)
            if forced:
                log["forced_submit"] = log.get("forced_submit", 0) + 1
                messages.append({"role": "user", "content": "Step limit reached. Submit your ranking now with "
                                                            "submit_ranking."})
            r = self.client.chat(messages, max_tokens=TURN_TOKENS, seed=seed,
                                 tools=(submit_only if forced else schemas) if native else None)
            self._count(r, log)
            log["steps"] = log.get("steps", 0) + 1
            actions = []
            if native and r["tool_calls"]:
                actions = [(c["id"], c["name"], c["arguments"]) for c in r["tool_calls"]]
                messages.append({"role": "assistant", "content": r["text"] or "", "tool_calls": [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in r["tool_calls"]]})
            else:
                parsed = parse_json_action(r["text"])
                messages.append({"role": "assistant", "content": r["text"] or ""})
                if parsed:
                    actions = [(None, parsed[0], parsed[1])]
                else:
                    final = parse_ranking(r["text"], labels) if forced or "submit" in (r["text"] or "").lower() else None
                    if final:
                        return [ordered.index(labelled[l]) for l in final]
                    log["invalid_actions"] = log.get("invalid_actions", 0) + 1
                    run_invalid += 1
                    samples = log.setdefault("invalid_samples", [])
                    if len(samples) < 2:
                        samples.append((r["text"] or "")[:400])
                    if forced:
                        break
                    messages.append({"role": "user", "content": 'Call one of the tools, for example {"name": '
                                     '"get_coverage", "arguments": {"label": "C1"}}, or submit_ranking.'})
                    continue
            for call_id, name, args in actions:
                if name == "submit_ranking":
                    final = parse_ranking(args.get("ranking"), labels) or parse_ranking(r["text"], labels)
                    if final is None:
                        log["unparsed_final"] = log.get("unparsed_final", 0) + 1
                        return None
                    return [ordered.index(labelled[l]) for l in final]
                answer, valid = tools.call(name, args)
                tool_steps += 1
                log["tool_calls"] = log.get("tool_calls", 0) + 1
                log.setdefault("tool_use", {})
                log["tool_use"][name] = log["tool_use"].get(name, 0) + 1
                if not valid:
                    log["invalid_actions"] = log.get("invalid_actions", 0) + 1
                if native and call_id is not None:
                    messages.append({"role": "tool", "tool_call_id": call_id, "content": answer})
                else:
                    messages.append({"role": "user", "content": f"RESULT of {name}:\n{answer}"})
        log["unparsed_final"] = log.get("unparsed_final", 0) + 1
        return None

    def judge(self, cands, failure, seed, log, ctx=None):
        analysis = prompts.failure_text(cands)
        n = len(cands)
        fwd_order = list(range(n))
        rev_order = list(reversed(range(n)))
        positions = {i: [] for i in range(n)}
        tops = []
        for name, order in (("forward", fwd_order), ("reversed", rev_order)):
            ranked = self._investigate(ctx or {}, analysis, [cands[i] for i in order], seed, log)
            if ranked is None:                      # no usable answer: this run contributes the shown order
                ranked = list(range(n))
                log.setdefault("failed_runs", []).append(name)
            mapped = [order[i] for i in ranked]
            log[f"ranking_{name}"] = [cands[i]["method_name"] for i in mapped]
            tops.append(mapped[0])
            for pos, i in enumerate(mapped):
                positions[i].append(pos)
        log["top1_agree"] = tops[0] == tops[1]
        mean = {i: sum(p) / len(p) for i, p in positions.items()}
        return sorted(range(n), key=lambda i: mean[i])    # stable: source order breaks equal means


from .selectors import REGISTRY  # noqa: E402

REGISTRY[S8b.name] = S8b()
