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

## Next selectors (model-based; see the spec)

S2 expected score from log-probabilities, S4 listwise with permutations, S5 pairwise in both orders, run on a
shortlist of the top candidates; then the same on the HypoDeduce lists with a shortlist that ignores the
hypothesis tier. These make new model calls (a few per bug) and are cached.
