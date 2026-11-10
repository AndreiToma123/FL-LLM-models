## Selection replay on runall-qwen25coder-csc-r1 (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 17; buggy method among the stored candidates in 206)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 124 | 190 | 199 | 0.402 | 0.367 | | | | |
| random ties, mean of 2000 (95% range) | 122.7 (113-132) | 186.1 | 199.2 | 0.399 | 0.365 | | | | |
| oracle tie-breaker (bound) | 192 | 203 | 205 | 0.508 | 0.461 | | | | |
| S0 | 124 | 190 | 199 | 0.402 | 0.367 | +0 | +1.3 | 2% | 1.000 |
| S0r | 118 | 183 | 199 | 0.392 | 0.358 | -6 | -4.7 | -7% | 0.471 |
| S1 | 125 | 185 | 197 | 0.402 | 0.369 | +1 | +2.3 | 3% | 1.000 |
| S6 | 138 | 194 | 201 | 0.424 | 0.388 | +14 | +15.3 | 22% | 0.003 |
| S5 | 160 | 198 | 204 | 0.458 | 0.415 | +36 | +37.3 | 54% | 0.000 |
| S5+S2 | 153 | 200 | 203 | 0.451 | 0.409 | +29 | +30.3 | 44% | 0.000 |
| S8a | 152 | 194 | 204 | 0.445 | 0.406 | +28 | +29.3 | 42% | 0.000 |
| S8a+S2 | 157 | 199 | 204 | 0.455 | 0.414 | +33 | +34.3 | 50% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 234 | 2698 | 0 | 3283616 | 873.3 | 775 / 1349 (775) | 192 |
| S5+S2 | qwen25coder | top-tie (8) | 234 | 432 | 2698 | 3701041 | 99.8 | 775 / 1349 (775) | 192 |
| S8a | qwen25coder | top-tie (8) | 234 | 2698 | 0 | 4868244 | 1033.5 | 897 / 1349 (897) | 192 |
| S8a+S2 | qwen25coder | top-tie (8) | 234 | 501 | 2698 | 5637289 | 140.1 | 897 / 1349 (897) | 192 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
