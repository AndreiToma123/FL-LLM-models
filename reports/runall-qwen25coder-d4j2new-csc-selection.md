## Selection replay on runall-qwen25coder-d4j2new-csc (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 2; buggy method among the stored candidates in 189)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 110 | 167 | 178 | 0.316 | 0.263 | | | | |
| random ties, mean of 2000 (95% range) | 108.0 (99-118) | 168.4 | 179.8 | 0.314 | 0.262 | | | | |
| oracle tie-breaker (bound) | 171 | 185 | 186 | 0.401 | 0.333 | | | | |
| S0 | 110 | 167 | 178 | 0.316 | 0.263 | +0 | +2.0 | 3% | 1.000 |
| S0r | 99 | 164 | 177 | 0.301 | 0.254 | -11 | -9.0 | -14% | 0.135 |
| S1 | 115 | 164 | 181 | 0.321 | 0.267 | +5 | +7.0 | 11% | 0.522 |
| S6 | 110 | 167 | 178 | 0.316 | 0.263 | +0 | +2.0 | 3% | 1.000 |
| S5 | 122 | 167 | 178 | 0.330 | 0.276 | +12 | +14.0 | 22% | 0.002 |
| S5+S2 | 128 | 170 | 180 | 0.341 | 0.284 | +18 | +20.0 | 32% | 0.011 |
| S8a | 110 | 167 | 178 | 0.316 | 0.263 | +0 | +2.0 | 3% | 1.000 |
| S8a+S2 | 110 | 167 | 178 | 0.316 | 0.263 | +0 | +2.0 | 3% | 1.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 254 | 2864 | 0 | 3195040 | 1038.7 | 1317 / 1432 (1317) | 169 |
| S5+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 254 | 744 | 2864 | 3875492 | 202.4 | 1317 / 1432 (1317) | 169 |
| S8a | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 0 (no context: 254) | 0 | 0 | 0 | 0 |  | 110 |
| S8a+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 0 (no context: 254) | 0 | 0 | 0 | 0 |  | 110 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
