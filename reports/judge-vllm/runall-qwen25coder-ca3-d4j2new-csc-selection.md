## Selection replay on runall-qwen25coder-ca3-d4j2new-csc (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 3; buggy method among the stored candidates in 253)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 107 | 191 | 213 | 0.344 | 0.288 | | | | |
| random ties, mean of 2000 (95% range) | 96.3 (86-107) | 169.2 | 205.0 | 0.320 | 0.265 | | | | |
| oracle tie-breaker (bound) | 222 | 233 | 243 | 0.519 | 0.429 | | | | |
| S0 | 107 | 191 | 213 | 0.344 | 0.288 | +0 | +10.7 | 8% | 1.000 |
| S0r | 91 | 164 | 205 | 0.310 | 0.252 | -16 | -5.3 | -4% | 0.052 |
| S1 | 125 | 188 | 213 | 0.368 | 0.304 | +18 | +28.7 | 23% | 0.020 |
| S6 | 125 | 194 | 216 | 0.369 | 0.306 | +18 | +28.7 | 23% | 0.005 |
| S5 | 143 | 207 | 223 | 0.403 | 0.333 | +36 | +46.7 | 37% | 0.000 |
| S5+S2 | 152 | 203 | 222 | 0.413 | 0.338 | +45 | +55.7 | 44% | 0.000 |
| S8a | 141 | 206 | 224 | 0.398 | 0.330 | +34 | +44.7 | 36% | 0.000 |
| S8a+S2 | 142 | 208 | 224 | 0.401 | 0.329 | +35 | +45.7 | 36% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 348 | 8516 | 0 | 9479954 | 2122.6 | 2178 / 4258 (2178) | 214 |
| S5+S2 | qwen25coder | top-tie (8) | 348 | 883 | 8516 | 10280184 | 240.4 | 2178 / 4258 (2178) | 214 |
| S8a | qwen25coder | top-tie (8) | 348 | 8516 | 0 | 13471208 | 2440.8 | 2418 / 4258 (2418) | 214 |
| S8a+S2 | qwen25coder | top-tie (8) | 348 | 1010 | 8516 | 14811965 | 346.4 | 2418 / 4258 (2418) | 214 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
