## Selection replay on runall-qwen25coder-hd-h5c5m3-d4j2new-csc (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 4; buggy method among the stored candidates in 279)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 119 | 188 | 219 | 0.365 | 0.301 | | | | |
| random ties, mean of 2000 (95% range) | 81.6 (71-93) | 164.1 | 202.3 | 0.301 | 0.249 | | | | |
| oracle tie-breaker (bound) | 223 | 235 | 241 | 0.524 | 0.428 | | | | |
| S0 | 119 | 188 | 219 | 0.365 | 0.301 | +0 | +37.4 | 26% | 1.000 |
| S6 | 129 | 191 | 219 | 0.380 | 0.319 | +10 | +47.4 | 34% | 0.121 |
| S5 | 155 | 213 | 233 | 0.426 | 0.351 | +36 | +73.4 | 52% | 0.000 |
| S5+S2 | 146 | 209 | 232 | 0.416 | 0.344 | +27 | +64.4 | 46% | 0.002 |
| S8a | 152 | 221 | 235 | 0.428 | 0.355 | +33 | +70.4 | 50% | 0.000 |
| S8a+S2 | 148 | 217 | 235 | 0.423 | 0.351 | +29 | +66.4 | 47% | 0.001 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-k (8) | 429 | 112 | 22408 | 14896602 | 6.0 | 5426 / 11260 (5426) | 248 |
| S5+S2 | qwen25coder | top-k (8) | 429 | 10 | 24248 | 15737373 | 0.6 | 5426 / 11260 (5426) | 248 |
| S8a | qwen25coder | top-k (8) | 429 | 112 | 22408 | 24365818 | 4.3 | 5376 / 11260 (5376) | 248 |
| S8a+S2 | qwen25coder | top-k (8) | 429 | 9 | 24339 | 25947772 | 0.4 | 5376 / 11260 (5376) | 248 |

Selectors: **S0** = source run's own order (ties in review order); **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
