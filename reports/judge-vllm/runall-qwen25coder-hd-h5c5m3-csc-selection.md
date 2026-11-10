## Selection replay on runall-qwen25coder-hd-h5c5m3-csc (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 19; buggy method among the stored candidates in 253)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 127 | 196 | 213 | 0.424 | 0.392 | | | | |
| random ties, mean of 2000 (95% range) | 90.0 (80-101) | 173.2 | 202.7 | 0.355 | 0.323 | | | | |
| oracle tie-breaker (bound) | 193 | 216 | 222 | 0.536 | 0.488 | | | | |
| S0 | 127 | 196 | 213 | 0.424 | 0.392 | +0 | +37.0 | 36% | 1.000 |
| S6 | 122 | 201 | 216 | 0.420 | 0.388 | -5 | +32.0 | 31% | 0.302 |
| S5 | 164 | 207 | 225 | 0.490 | 0.449 | +37 | +74.0 | 72% | 0.000 |
| S5+S2 | 161 | 205 | 223 | 0.483 | 0.442 | +34 | +71.0 | 69% | 0.000 |
| S8a | 157 | 212 | 226 | 0.483 | 0.445 | +30 | +67.0 | 65% | 0.000 |
| S8a+S2 | 152 | 214 | 227 | 0.478 | 0.439 | +25 | +62.0 | 60% | 0.004 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-k (8) | 354 | 15662 | 1344 | 12655784 | 3748.5 | 4066 / 8503 (4066) | 231 |
| S5+S2 | qwen25coder | top-k (8) | 354 | 1230 | 17127 | 13357250 | 270.2 | 4066 / 8503 (4066) | 231 |
| S8a | qwen25coder | top-k (8) | 354 | 15662 | 1344 | 21619534 | 4183.8 | 3993 / 8503 (3993) | 231 |
| S8a+S2 | qwen25coder | top-k (8) | 354 | 1269 | 17127 | 23047840 | 383.9 | 3993 / 8503 (3993) | 231 |

Selectors: **S0** = source run's own order (ties in review order); **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
