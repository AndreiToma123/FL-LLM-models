## Selection replay on runall-qwen25coder-ca3g-csc (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 19; buggy method among the stored candidates in 240)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 124 | 200 | 215 | 0.421 | 0.384 | | | | |
| random ties, mean of 2000 (95% range) | 121.2 (111-131) | 195.6 | 214.4 | 0.415 | 0.375 | | | | |
| oracle tie-breaker (bound) | 216 | 229 | 230 | 0.575 | 0.516 | | | | |
| S0 | 124 | 200 | 215 | 0.421 | 0.384 | +0 | +2.8 | 3% | 1.000 |
| S0r | 116 | 198 | 215 | 0.412 | 0.371 | -8 | -5.2 | -6% | 0.358 |
| S1 | 141 | 199 | 219 | 0.448 | 0.401 | +17 | +19.8 | 21% | 0.027 |
| S6 | 132 | 208 | 220 | 0.439 | 0.401 | +8 | +10.8 | 11% | 0.134 |
| S5 | 159 | 214 | 221 | 0.483 | 0.437 | +35 | +37.8 | 40% | 0.000 |
| S5+S2 | 163 | 212 | 223 | 0.489 | 0.439 | +39 | +41.8 | 44% | 0.000 |
| S8a | 154 | 213 | 221 | 0.474 | 0.429 | +30 | +32.8 | 35% | 0.000 |
| S8a+S2 | 158 | 214 | 222 | 0.482 | 0.436 | +34 | +36.8 | 39% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 253 | 4498 | 0 | 5455236 | 1323.3 | 1290 / 2249 (1290) | 211 |
| S5+S2 | qwen25coder | top-tie (8) | 253 | 556 | 4498 | 6003230 | 141.4 | 1290 / 2249 (1290) | 211 |
| S8a | qwen25coder | top-tie (8) | 253 | 4498 | 0 | 8070476 | 1561.7 | 1401 / 2249 (1401) | 211 |
| S8a+S2 | qwen25coder | top-tie (8) | 253 | 636 | 4498 | 9041779 | 213.4 | 1401 / 2249 (1401) | 211 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
