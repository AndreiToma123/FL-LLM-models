## Selection replay on runall-qwen25coder-ca3-csc (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 21; buggy method among the stored candidates in 259)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 134 | 206 | 234 | 0.449 | 0.414 | | | | |
| random ties, mean of 2000 (95% range) | 113.9 (103-125) | 191.8 | 222.8 | 0.411 | 0.375 | | | | |
| oracle tie-breaker (bound) | 234 | 248 | 254 | 0.623 | 0.567 | | | | |
| S0 | 134 | 206 | 234 | 0.449 | 0.414 | +0 | +20.1 | 17% | 1.000 |
| S6 | 140 | 215 | 235 | 0.464 | 0.429 | +6 | +26.1 | 22% | 0.286 |
| S8a+S2 | 163 | 225 | 242 | 0.504 | 0.458 | +29 | +49.1 | 41% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S8a+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 286 | 7215 | 19 | 12585713 | 2600.0 | 2703 / 3087 (2703) | 229 |

Selectors: **S0** = source run's own order (ties in review order); **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
