## Selection replay on runall-qwen25coder-d4j2new-csc-r1 (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 1; buggy method among the stored candidates in 185)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 104 | 163 | 177 | 0.303 | 0.254 | | | | |
| random ties, mean of 2000 (95% range) | 107.3 (98-117) | 164.7 | 176.2 | 0.309 | 0.255 | | | | |
| oracle tie-breaker (bound) | 167 | 179 | 184 | 0.391 | 0.320 | | | | |
| S0 | 104 | 163 | 177 | 0.303 | 0.254 | +0 | -3.3 | -6% | 1.000 |
| S0r | 107 | 158 | 170 | 0.304 | 0.253 | +3 | -0.3 | -1% | 0.755 |
| S1 | 125 | 168 | 178 | 0.331 | 0.273 | +21 | +17.7 | 30% | 0.001 |
| S6 | 116 | 166 | 177 | 0.321 | 0.268 | +12 | +8.7 | 14% | 0.008 |
| S5 | 129 | 172 | 178 | 0.340 | 0.279 | +25 | +21.7 | 36% | 0.000 |
| S5+S2 | 136 | 172 | 178 | 0.348 | 0.285 | +32 | +28.7 | 48% | 0.000 |
| S8a | 126 | 170 | 177 | 0.336 | 0.278 | +22 | +18.7 | 31% | 0.000 |
| S8a+S2 | 138 | 170 | 178 | 0.349 | 0.286 | +34 | +30.7 | 51% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 254 | 2742 | 0 | 3022804 | 756.7 | 699 / 1371 (699) | 167 |
| S5+S2 | qwen25coder | top-tie (8) | 254 | 438 | 2742 | 3418151 | 86.8 | 699 / 1371 (699) | 167 |
| S8a | qwen25coder | top-tie (8) | 254 | 2742 | 0 | 4307320 | 898.8 | 763 / 1371 (763) | 167 |
| S8a+S2 | qwen25coder | top-tie (8) | 254 | 491 | 2742 | 4955373 | 108.2 | 763 / 1371 (763) | 167 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
