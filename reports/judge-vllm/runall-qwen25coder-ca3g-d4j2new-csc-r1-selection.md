## Selection replay on runall-qwen25coder-ca3g-d4j2new-csc-r1 (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 2; buggy method among the stored candidates in 234)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 111 | 177 | 202 | 0.335 | 0.282 | | | | |
| random ties, mean of 2000 (95% range) | 108.3 (98-119) | 177.4 | 200.3 | 0.334 | 0.278 | | | | |
| oracle tie-breaker (bound) | 203 | 215 | 227 | 0.476 | 0.393 | | | | |
| S0 | 111 | 177 | 202 | 0.335 | 0.282 | +0 | +2.7 | 3% | 1.000 |
| S0r | 100 | 177 | 198 | 0.321 | 0.267 | -11 | -8.3 | -9% | 0.135 |
| S1 | 129 | 185 | 205 | 0.364 | 0.304 | +18 | +20.7 | 22% | 0.020 |
| S6 | 124 | 178 | 206 | 0.354 | 0.296 | +13 | +15.7 | 16% | 0.041 |
| S5 | 137 | 186 | 206 | 0.374 | 0.311 | +26 | +28.7 | 30% | 0.000 |
| S5+S2 | 144 | 188 | 205 | 0.383 | 0.316 | +33 | +35.7 | 38% | 0.000 |
| S8a | 138 | 187 | 204 | 0.374 | 0.314 | +27 | +29.7 | 31% | 0.000 |
| S8a+S2 | 143 | 187 | 205 | 0.381 | 0.318 | +32 | +34.7 | 37% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 321 | 5854 | 0 | 6606296 | 1554.6 | 1646 / 2927 (1646) | 194 |
| S5+S2 | qwen25coder | top-tie (8) | 321 | 730 | 5854 | 7274290 | 188.3 | 1646 / 2927 (1646) | 194 |
| S8a | qwen25coder | top-tie (8) | 321 | 5854 | 0 | 9433058 | 1776.9 | 1753 / 2927 (1753) | 194 |
| S8a+S2 | qwen25coder | top-tie (8) | 321 | 823 | 5854 | 10546535 | 269.5 | 1753 / 2927 (1753) | 194 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
