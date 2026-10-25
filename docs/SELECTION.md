# Final-selection framework (RQ3)

Design spec: `claude/SELECTION_FRAMEWORK_SPEC.md` (project docs). Code: `fl_tools/selection/`.

## Idea: replay on stored candidate lists

Every finished run stores, per bug, the candidate methods it scored (`result.json` → `buggy_methods`).
A **selector** takes that list and returns a new order. No front-end re-run is needed, so selection
strategies can be developed on the 100 baseline bugs and on the HypoDeduce lists without running the
expensive pipelines again. Only model-based selectors make (few) new model calls.

```
python -m fl_tools select --list                                   # available selectors
python -m fl_tools select reports/run100-qwen25coder               # dev part of the split only
python -m fl_tools select reports/run100-qwen25coder --reveal-test # once, after choosing on dev
python -m fl_tools select reports/run10of100-qwen25coder-hd-h5c5m3 --split none   # HypoDeduce lists (test-only)
```

Output: one run folder per selector, `reports/<run>-sel-<selector>/` (same layout as an exported run,
so `score`, `funnel`, `ties`, `compare` work on it), plus `reports/<run>-selection.md/.json` with
Top-1/3/5, MRR, MAP, the random-ties expectation (S0r), the oracle bound, gain over the source order and
over random ties, the share of the oracle gap recovered and an exact McNemar test against the source order.

Rules built in: selectors only reorder methods **inside** the source run's ties (equal sort keys);
the dev/test split of the 100 bugs (`configs/selection_split.json`, stratified by project, seed 20261024)
hides the test part unless `--reveal-test` is given; bugs that crashed in the source run count as misses.

## Selectors so far (no model calls)

| Name | What it does |
|---|---|
| S0 | source order (SoapFL: ties in review order) |
| S0r | random order inside ties (one seeded draw; the expectation over 2000 draws is reported as the reference) |
| S1 | lexical evidence, in this order: the failure analysis names the method literally; share of the method-name tokens found in the failure analysis; TF-IDF similarity of the method (name, doc, code) to the failure analysis |
| S1-body | only the TF-IDF similarity |

The failure analysis is the bug-level text the pipeline wrote before ranking (`test_failure_causes`). The
model's per-method justification and score are not used as features (they are what is being re-judged).
S1 was fixed before looking at results; its key order is not tuned.

## Results so far (2026-10-24, qwen2.5-coder 7B lists, no new model calls)

Baseline `run100-qwen25coder` (S0 reproduces 28/46/47; random ties 28.8, 95% range 24-34; oracle 48):

| Part | Source (S0) | Random ties, mean (95%) | Oracle | S1 | S1-body |
|---|---:|---:|---:|---:|---:|
| dev, 50 bugs, Top-1 | 16 | 15.5 (12-19) | 27 | **18** | 17 |
| test, 50 bugs, Top-1 | 12 | 13.3 (10-16) | 21 | 14 | 14 |
| all, 100 bugs, Top-1 | 28 | 28.8 (24-34) | 48 | 32 (McNemar p = 0.29) | 31 |

* Chosen on dev: S1. On test it is inside the random-ties range: **lexical tie-breaking gives at most a small,
  non-significant gain** (about 16% of the oracle gap over 100 bugs). This matches the pre-registered
  expectation in the spec (S1 alone is unlikely to beat random by much).
* Honesty note: the test part was printed once during development, before the `--reveal-test` gate existed.
  No choice was changed after seeing it.

HypoDeduce `run10of100-qwen25coder-hd-h5c5m3` (9 bugs with output, test-only): source 0/2/3, random ties 0.5,
oracle only 3, S1 0/1/3. The oracle is low because HypoDeduce's ties are inside hypothesis tiers: the buggy
method is often below all methods of the selected hypothesis, where a tie-breaker cannot reach it. For these
lists a selector must be allowed to re-rank a shortlist across tiers (next step).

## Model-based selectors: S5 pairwise, then S2 log-prob as a second layer

Code: `fl_tools/selection/judges.py`, prompts `prompts.py` (their hash is stored as `prompt_version`), client
`llm.py` (same endpoint variables as the pipelines: `SOAPFL_BASE_URL` or `SOAPFL_UDS`).

| Name | What it does | Calls per bug (shortlist of n) |
|---|---|---|
| S5 | every pair of shortlisted methods is shown in **both orders** ("A or B?"); a pair is a win only if both answers agree, else a draw. Ranked by Copeland score (wins - losses); remaining ties keep the source order | n(n-1) |
| S2 | one call per method asks for one digit 0-9; the score is the expected value over the digit tokens' log-probabilities (continuous, so far fewer ties than SoapFL's integer scores) | n |
| S5+S2 | S5 first; methods still tied on Copeland score are ordered by S2 (computed only for them) | n(n-1) + tied |

Shortlist (`--shortlist`, at most `--k` methods, default 8): `top-tie` = the tied top group of the source
run (SoapFL lists; only this group decides Top-1), `top-k` = the K best raw scores across HypoDeduce's
hypothesis tiers. The report adds, per model-based selector: bugs judged, new and cached calls, tokens,
seconds, drawn pairs and position-inconsistent pairs (both orders answered, but the answers disagree:
a direct measure of position bias), and how many Top-1 hits the shortlist makes reachable.

Inputs shown to the judge: the failure analysis the source run stored and the method name (without
package), documentation and code. Never the bug id, the project, the ground truth, or the source run's
score and reason. Temperature 0, fixed seed; every answer is cached in `results/judge_cache.jsonl`, so
re-running (or revealing the test part) repeats no call. While the test part is hidden, only the dev bugs
are judged.

Local (Windows, Docker + Ollama):

```
run-select.cmd --check-logprobs                                  # does Ollama return log-probs? (needed for S2)
run-select.cmd reports/run100-qwen25coder --selector S5          # dev only: 35 bugs, about 408 short calls
run-select.cmd reports/run100-qwen25coder --selector S5+S2       # adds about 120 calls at most, cached S5 reused
run-select.cmd reports/run100-qwen25coder --selector S0,S1,S5,S5+S2 --reveal-test   # once, choices frozen
run-select.cmd reports/run10of100-qwen25coder-hd-h5c5m3 --split none --shortlist top-k --selector S5,S5+S2
```

Cost estimate for the baseline (top-tie, K = 8): dev 35 judged bugs, 408 S5 calls and at most 123 S2
calls; all 100 bugs 65 judged, 762 S5 calls, at most 226 S2 calls. Prompts are about 1.7k tokens and the
answer 1-2 tokens, so a call costs about the prompt processing time. K = 8 loses no reachable hit on the
baseline (shortlist reach = tie oracle: 27 dev, 48 all).

If the endpoint returns no log-probabilities, S2 and S5+S2 stop with a clear message; S5 still runs.
vLLM on CSC returns them.

## Failure context, S6, S8a, S8b and gated escalation (built 2026-10-25)

Order agreed with the user: failure-context export -> S8a -> S8b -> B (scored from the cache) -> C (HypoDeduce
hypothesis testing) only if S8 beats S5 on dev.

**Failure context** (`fl_tools/context.py`, `python -m fl_tools context <run folder> ...` (reports/ or results/), Windows
`run-context.cmd`): per bug, model-independent, `results/_failure_context/<d4j dir>.json`, copied to
`reports/_failure_context/`. Contents: failing tests (at most 3; total recorded) with error output, stack
trace, parsed frames, test method source (failing line marked by SoapFL) and helper methods; per production
method executed by the failing tests: how many failing tests executed it and its smallest stack depth; source
of executed methods in the classes on the stack and the candidates' classes (capped). Uses SoapFL's own
helpers (instrumentation agent, tree-sitter). Never: the fixed version, `classes.modified`, VCS history, bug
reports, SoapFL's `buggy_methods`. Reuses the buggy checkout a run left in `results/`, else checks out the
buggy version only. CPU only, resumable (`--bugs`, `--part dev`, `--jobs`).

| Name | Model calls | What it does |
|---|---|---|
| S6 | none | inside ties: methods on a failing test's stack first (shallower first), then share of failing tests that executed them |
| S8a | n(n-1) | S5 (pairwise, both orders, Copeland) with a fixed evidence bundle: failing tests, error, project frames, test code, and per method its stack depth and coverage |
| S8a-lp | n | S2 (log-prob 0-9) with the same bundle |
| S8a+S2 | n(n-1) + tied | S5+S2 with the same bundle (S8a's pairs, then the evidence log-prob score breaks the draws) |
| S8b | <= 2 x (steps + 1) | agent: read-only tools over the frozen context (`list_failing_tests`, `get_test`, `get_stack_trace`, `get_candidate`, `get_coverage`, `search_methods`, `get_method_code`, `submit_ranking`), step cap `--agent-steps` (6); run with candidates in source order and reversed, combined by mean position; logs turns, tool use, invalid actions, forced submits, forward/reversed top-1 agreement |

S8a vs S5 measures the value of the evidence with the decision rule fixed; S8b vs S8a measures the value of
the loop (the model choosing what to look at). Protocols for S8b: `--agent-protocol native` (OpenAI tool
calls; check with `--check-tools`) or `json` (one JSON action per turn). Bugs without a context file keep the
source order and are counted ("no context").

**B, gated escalation, offline** (`fl_tools/selection/gate.py`, `python -m fl_tools gate <run> --ladder
S6,S5,S8a,S8b`): reads the existing `-sel-*` replays, scores every ordered sub-ladder (S0 > ... ) and reports
Top-1/3, MRR, model calls per bug, where bugs stopped, and the Pareto front (Top-1 vs calls). Confidence per
step: S0 no top tie; S5/S8a unique Copeland top; S2/S8a-lp expected-score gap >= `--margin`; S8b forward and
reversed agree; S6 strict key order. No new model calls.

Local smoke tests (within the 2-hour local limit), then full runs on CSC:

```
run-select.cmd reports/run100-qwen25coder --check-tools --check-logprobs
run-context.cmd reports/run100-qwen25coder --bugs Lang-1,Closure-105          # smoke: check the files, time per bug
run-context.cmd reports/run100-qwen25coder --part dev --jobs 4                # 50 dev bugs, CPU only
run-select.cmd reports/run100-qwen25coder --selector S6,S8a                    # S8a: about 408 calls
run-select.cmd reports/run100-qwen25coder --selector S8b                       # about 2 x 7 turns per judged bug
docker compose run --rm soapfl python -m fl_tools gate reports/run100-qwen25coder --ladder S6,S5,S8a,S8b
```

### First real runs (2026-10-25, dev, 50 bugs; qwen2.5-coder 7B via Ollama)

| Selector | Top-1 | Top-3 | MRR | gains / losses vs source | McNemar p | model calls |
|---|---:|---:|---:|---:|---:|---:|
| S0 source | 16 | 25 | 0.414 | | | 0 |
| S6 stack/coverage | 16 | 26 | 0.422 | 0 / 0 | 1.0 | 0 |
| S5 pairwise | 19 | 25 | 0.447 | 3 / 0 | 0.25 | 408 |
| S5+S2 | 20 | 26 | 0.467 | 5 / 1 | 0.22 | 509 |
| S8a evidence pairwise | 20 | 25 | 0.457 | 4 / 0 | 0.125 | 408 |
| S8b agent (first version) | 16 | 25 | 0.414 | 0 / 0 | 1.0 | 390 |

Failure context: 47 of 50 dev bugs (3 Mockito infrastructure crashes have no candidates), median 25 s per bug,
24 CPU-minutes in total. 27 of the 35 judged bugs fail on an assertion, so the buggy method is rarely on the
stack (a shortlisted candidate is on the stack in 7 bugs, the buggy method in 5): this is why S6 cannot help.
S8a still draws 177 of 204 pairs (S5: 181): the evidence does not remove the position bias.
S8b first version: the model never produced a native tool call (0 tool calls, 360 invalid turns, 40 of 70
investigations without a usable ranking). Fixed: tool calls written as text (Qwen/Hermes `{"name",
"arguments"}`, `<tool_call>` tags, code fences, OpenAI-style objects) are now accepted; after two invalid replies
the agent is asked to submit; the first invalid replies are stored per bug (`invalid_samples`). Needs a re-run.

### Frozen before the test reveal (user decision, 2026-10-25 ~10:00)

Fixed on dev only, before any test-part result of these selectors was seen:
* **Primary:** S8a+S2 (top-tie shortlist, K = 8; judge = the source run's model, qwen2.5-coder 7B via Ollama;
  prompt hash with evidence `75b2b186403e`). Primary comparison: Top-1 vs the source order (exact McNemar) and
  vs the random-ties range.
* **Secondary (reported, no claims):** S5, S5+S2, S8a, S8b (6 steps, native protocol), S6, S1, and the gate
  policy S0 > S6 > S8a+S2 (margin 0.5).
* **Not run:** C (agentic hypothesis testing inside HypoDeduce), by the pre-agreed stop rule: S8b (17) did not
  beat S5 (19) on dev.
* Known dev caveat: many selectors were compared on the same 50 dev bugs; the dev numbers are optimistic.

### Test reveal (2026-10-25, run once with the frozen choices)

| Top-1 | dev 50 | test 50 | all 100 | McNemar p vs source (test / all) |
|---|---:|---:|---:|---:|
| source order | 16 | 12 | 28 | |
| random ties, 95% range | 12-19 | 10-16 | 24-34 | |
| S5 | 19 | 15 | 34 | 0.375 / 0.070 |
| S5+S2 | 20 | 16 | 36 | 0.219 / 0.039 |
| S8a | 20 | 14 | 34 | 0.625 / 0.070 |
| **S8a+S2 (primary)** | 21 | **16** | 37 | **0.219** / 0.022 |
| S8b | 17 | 13 | 30 | 1.0 / 0.625 |
| S6 | 16 | 13 | 29 | 1.0 / 1.0 |
| gate S0 > S6 > S8a+S2 (calls/bug) | 21 (9.0) | 16 (4.8) | 37 (6.9) | |

Primary on test: +4 (5 gains, 1 loss), not significant, at the top of the random-ties range. The 100-bug p-values
include the dev half used for choosing and are optimistic. On test the evidence bundle adds nothing (S8a+S2 and
S5+S2 have the same gains and losses); the log-prob layer adds +1 on both halves; the agent is a negative result;
gating keeps Top-1 at about half the model calls on test.
