## Selection replay on runall-qwen25coder-ca3g-csc-r1 (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 21; buggy method among the stored candidates in 236)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 132 | 203 | 217 | 0.433 | 0.394 | | | | |
| random ties, mean of 2000 (95% range) | 124.6 (114-135) | 198.2 | 216.2 | 0.422 | 0.384 | | | | |
| oracle tie-breaker (bound) | 217 | 230 | 233 | 0.577 | 0.518 | | | | |
| S0 | 132 | 203 | 217 | 0.433 | 0.394 | +0 | +7.3 | 8% | 1.000 |
| S0r | 119 | 200 | 219 | 0.412 | 0.378 | -13 | -5.7 | -6% | 0.098 |
| S1 | 142 | 207 | 221 | 0.456 | 0.413 | +10 | +17.4 | 19% | 0.253 |
| S6 | 138 | 209 | 220 | 0.446 | 0.408 | +6 | +13.3 | 14% | 0.263 |
| S5 | 165 | 216 | 224 | 0.490 | 0.444 | +33 | +40.4 | 44% | 0.000 |
| S5+S2 | 166 | 218 | 224 | 0.494 | 0.447 | +34 | +41.4 | 45% | 0.000 |
| S8a | 161 | 216 | 223 | 0.484 | 0.440 | +29 | +36.4 | 39% | 0.000 |
| S8a+S2 | 160 | 217 | 223 | 0.484 | 0.441 | +28 | +35.4 | 38% | 0.001 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 252 | 4128 | 0 | 4934582 | 1224.1 | 1137 / 2064 (1137) | 213 |
| S5+S2 | qwen25coder | top-tie (8) | 252 | 528 | 4128 | 5442529 | 134.3 | 1137 / 2064 (1137) | 213 |
| S8a | qwen25coder | top-tie (8) | 252 | 4128 | 0 | 7279092 | 1441.1 | 1256 / 2064 (1256) | 213 |
| S8a+S2 | qwen25coder | top-tie (8) | 252 | 606 | 4128 | 8180735 | 200.0 | 1256 / 2064 (1256) | 213 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
