## Selection replay on runall-qwen25coder-csc (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 17; buggy method among the stored candidates in 207)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 130 | 191 | 199 | 0.412 | 0.378 | | | | |
| random ties, mean of 2000 (95% range) | 120.9 (112-130) | 187.2 | 199.1 | 0.397 | 0.363 | | | | |
| oracle tie-breaker (bound) | 187 | 206 | 207 | 0.505 | 0.460 | | | | |
| S0 | 130 | 191 | 199 | 0.412 | 0.378 | +0 | +9.1 | 14% | 1.000 |
| S0r | 115 | 187 | 201 | 0.390 | 0.358 | -15 | -5.9 | -9% | 0.049 |
| S1 | 128 | 192 | 199 | 0.409 | 0.374 | -2 | +7.1 | 11% | 0.885 |
| S6 | 136 | 193 | 200 | 0.422 | 0.387 | +6 | +15.1 | 23% | 0.263 |
| S5 | 151 | 196 | 201 | 0.443 | 0.405 | +21 | +30.1 | 46% | 0.001 |
| S5+S2 | 156 | 197 | 201 | 0.453 | 0.413 | +26 | +35.1 | 53% | 0.000 |
| S8a | 151 | 196 | 201 | 0.443 | 0.404 | +21 | +30.1 | 46% | 0.000 |
| S8a+S2 | 152 | 195 | 201 | 0.446 | 0.405 | +22 | +31.1 | 47% | 0.001 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 214 | 2390 | 0 | 2911962 | 794.4 | 673 / 1195 (673) | 184 |
| S5+S2 | qwen25coder | top-tie (8) | 214 | 400 | 2390 | 3298790 | 98.3 | 673 / 1195 (673) | 184 |
| S8a | qwen25coder | top-tie (8) | 214 | 2390 | 0 | 4317190 | 946.1 | 756 / 1195 (756) | 184 |
| S8a+S2 | qwen25coder | top-tie (8) | 214 | 440 | 2390 | 4991638 | 115.8 | 756 / 1195 (756) | 184 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
