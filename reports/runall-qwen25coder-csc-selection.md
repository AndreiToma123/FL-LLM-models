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
| S5 | 143 | 193 | 200 | 0.430 | 0.395 | +13 | +22.1 | 33% | 0.007 |
| S5+S2 | 148 | 197 | 201 | 0.439 | 0.400 | +18 | +27.1 | 41% | 0.015 |
| S8a | 145 | 195 | 200 | 0.436 | 0.400 | +15 | +24.1 | 36% | 0.003 |
| S8a+S2 | 150 | 197 | 201 | 0.445 | 0.405 | +20 | +29.1 | 44% | 0.005 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 214 | 2390 | 0 | 2911962 | 986.3 | 1103 / 1195 (1103) | 184 |
| S5+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 214 | 645 | 2390 | 3543261 | 258.6 | 1103 / 1195 (1103) | 184 |
| S8a | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 214 | 2390 | 0 | 4317190 | 1055.8 | 1061 / 1195 (1061) | 184 |
| S8a+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 214 | 607 | 2390 | 5248586 | 267.4 | 1061 / 1195 (1061) | 184 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
