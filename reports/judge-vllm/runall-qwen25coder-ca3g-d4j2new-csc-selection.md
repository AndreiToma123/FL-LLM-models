## Selection replay on runall-qwen25coder-ca3g-d4j2new-csc (444 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### all (444 bugs; infrastructure failures 2; buggy method among the stored candidates in 236)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 118 | 186 | 206 | 0.351 | 0.293 | | | | |
| random ties, mean of 2000 (95% range) | 112.5 (103-122) | 184.1 | 203.5 | 0.343 | 0.286 | | | | |
| oracle tie-breaker (bound) | 206 | 222 | 226 | 0.486 | 0.400 | | | | |
| S0 | 118 | 186 | 206 | 0.351 | 0.293 | +0 | +5.5 | 6% | 1.000 |
| S0r | 114 | 183 | 206 | 0.345 | 0.287 | -4 | +1.5 | 2% | 0.683 |
| S1 | 133 | 189 | 206 | 0.372 | 0.305 | +15 | +20.5 | 22% | 0.063 |
| S6 | 127 | 194 | 206 | 0.367 | 0.307 | +9 | +14.5 | 16% | 0.150 |
| S5 | 143 | 196 | 210 | 0.388 | 0.324 | +25 | +30.5 | 33% | 0.000 |
| S5+S2 | 148 | 198 | 210 | 0.394 | 0.328 | +30 | +35.5 | 38% | 0.000 |
| S8a | 143 | 195 | 209 | 0.389 | 0.324 | +25 | +30.5 | 33% | 0.000 |
| S8a+S2 | 145 | 196 | 210 | 0.392 | 0.326 | +27 | +32.5 | 35% | 0.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | qwen25coder | top-tie (8) | 304 | 6444 | 0 | 7094054 | 1612.8 | 1745 / 3222 (1745) | 198 |
| S5+S2 | qwen25coder | top-tie (8) | 304 | 715 | 6444 | 7738504 | 184.5 | 1745 / 3222 (1745) | 198 |
| S8a | qwen25coder | top-tie (8) | 304 | 6444 | 0 | 10007388 | 1873.1 | 1975 / 3222 (1975) | 198 |
| S8a+S2 | qwen25coder | top-tie (8) | 304 | 830 | 6444 | 11103610 | 267.9 | 1975 / 3222 (1975) | 198 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
