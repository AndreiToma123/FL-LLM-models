## Selection replay on runall-qwen25coder-ca3-csc-r1 (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 19; buggy method among the stored candidates in 257)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 133 | 210 | 229 | 0.452 | 0.407 | | | | |
| random ties, mean of 2000 (95% range) | 111.5 (101-123) | 191.7 | 222.0 | 0.407 | 0.365 | | | | |
| oracle tie-breaker (bound) | 233 | 251 | 255 | 0.625 | 0.557 | | | | |
| S0 | 133 | 210 | 229 | 0.452 | 0.407 | +0 | +21.5 | 18% | 1.000 |
| S0r | 104 | 181 | 216 | 0.387 | 0.351 | -29 | -7.5 | -6% | 0.001 |
| S1 | 136 | 212 | 235 | 0.460 | 0.411 | +3 | +24.5 | 20% | 0.798 |
| S6 | 135 | 213 | 236 | 0.459 | 0.415 | +2 | +23.5 | 19% | 0.839 |
| S5 | 175 | 231 | 241 | 0.524 | 0.472 | +42 | +63.5 | 52% | 0.000 |
| S5+S2 | 174 | 230 | 240 | 0.523 | 0.471 | +41 | +62.5 | 52% | 0.000 |
| S8a | 171 | 225 | 237 | 0.517 | 0.468 | +38 | +59.5 | 49% | 0.000 |
| S8a+S2 | 170 | 227 | 239 | 0.518 | 0.470 | +37 | +58.5 | 48% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 276 | 6064 | 0 | 7356532 | 1764.3 | 1538 / 3032 (1538) | 229 |
| S5+S2 | qwen25coder | top-tie (8) | 276 | 662 | 6064 | 7994521 | 183.0 | 1538 / 3032 (1538) | 229 |
| S8a | qwen25coder | top-tie (8) | 276 | 6064 | 0 | 10908478 | 2037.7 | 1682 / 3032 (1682) | 229 |
| S8a+S2 | qwen25coder | top-tie (8) | 276 | 737 | 6064 | 12019386 | 272.0 | 1682 / 3032 (1682) | 229 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
