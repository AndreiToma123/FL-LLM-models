## Selection replay on runall-qwen25coder-ca3-d4j2new-csc-r1 (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 2; buggy method among the stored candidates in 252)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 117 | 189 | 215 | 0.356 | 0.302 | | | | |
| random ties, mean of 2000 (95% range) | 102.0 (92-113) | 176.8 | 209.6 | 0.331 | 0.279 | | | | |
| oracle tie-breaker (bound) | 224 | 237 | 243 | 0.522 | 0.435 | | | | |
| S0 | 117 | 189 | 215 | 0.356 | 0.302 | +0 | +15.0 | 12% | 1.000 |
| S0r | 103 | 175 | 207 | 0.331 | 0.274 | -14 | +1.0 | 1% | 0.114 |
| S1 | 124 | 182 | 216 | 0.363 | 0.306 | +7 | +22.0 | 18% | 0.419 |
| S6 | 128 | 187 | 219 | 0.371 | 0.317 | +11 | +26.0 | 21% | 0.080 |
| S5 | 147 | 205 | 224 | 0.405 | 0.343 | +30 | +45.0 | 37% | 0.000 |
| S5+S2 | 147 | 209 | 224 | 0.408 | 0.342 | +30 | +45.0 | 37% | 0.000 |
| S8a | 145 | 205 | 220 | 0.401 | 0.341 | +28 | +43.0 | 35% | 0.000 |
| S8a+S2 | 145 | 207 | 221 | 0.403 | 0.343 | +28 | +43.0 | 35% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 340 | 8016 | 0 | 8778114 | 1982.6 | 2130 / 4008 (2130) | 215 |
| S5+S2 | qwen25coder | top-tie (8) | 340 | 898 | 8016 | 9582815 | 236.7 | 2130 / 4008 (2130) | 215 |
| S8a | qwen25coder | top-tie (8) | 340 | 8016 | 0 | 12496496 | 2280.5 | 2269 / 4008 (2269) | 215 |
| S8a+S2 | qwen25coder | top-tie (8) | 340 | 963 | 8016 | 13765418 | 335.1 | 2269 / 4008 (2269) | 215 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
