## Selection replay on runall-qwen25coder-ca3-csc (388 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (388 bugs; infrastructure failures 21; buggy method among the stored candidates in 259)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 134 | 206 | 234 | 0.449 | 0.414 | | | | |
| random ties, mean of 2000 (95% range) | 113.9 (103-125) | 191.8 | 222.8 | 0.411 | 0.375 | | | | |
| oracle tie-breaker (bound) | 234 | 248 | 254 | 0.623 | 0.567 | | | | |
| S0 | 134 | 206 | 234 | 0.449 | 0.414 | +0 | +20.1 | 17% | 1.000 |
| S0r | 110 | 190 | 230 | 0.405 | 0.369 | -24 | -3.9 | -3% | 0.004 |
| S1 | 142 | 205 | 230 | 0.466 | 0.426 | +8 | +28.1 | 23% | 0.422 |
| S6 | 140 | 215 | 235 | 0.464 | 0.429 | +6 | +26.1 | 22% | 0.286 |
| S5 | 169 | 224 | 240 | 0.514 | 0.473 | +35 | +55.1 | 46% | 0.000 |
| S5+S2 | 176 | 226 | 240 | 0.524 | 0.480 | +42 | +62.1 | 52% | 0.000 |
| S8a | 173 | 224 | 239 | 0.519 | 0.474 | +39 | +59.1 | 49% | 0.000 |
| S8a+S2 | 172 | 225 | 242 | 0.519 | 0.474 | +38 | +58.1 | 48% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 286 | 6174 | 0 | 7432600 | 1810.5 | 1549 / 3087 (1549) | 229 |
| S5+S2 | qwen25coder | top-tie (8) | 286 | 656 | 6174 | 8064047 | 191.9 | 1549 / 3087 (1549) | 229 |
| S8a | qwen25coder | top-tie (8) | 286 | 6174 | 0 | 10990092 | 2097.7 | 1791 / 3087 (1791) | 229 |
| S8a+S2 | qwen25coder | top-tie (8) | 286 | 773 | 6174 | 12159800 | 297.0 | 1791 / 3087 (1791) | 229 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
