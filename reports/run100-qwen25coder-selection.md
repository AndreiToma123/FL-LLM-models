## Selection replay on run100-qwen25coder (100 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### dev (50 bugs; infrastructure failures 3; buggy method among the stored candidates in 29)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 16 | 25 | 25 | 0.414 | 0.381 | | | | |
| random ties, mean of 2000 (95% range) | 15.5 (12-19) | 23.9 | 27.2 | 0.404 | 0.369 | | | | |
| oracle tie-breaker (bound) | 27 | 28 | 29 | 0.554 | 0.511 | | | | |
| S0 | 16 | 25 | 25 | 0.414 | 0.381 | +0 | +0.6 | 5% | 1.000 |
| S0r | 14 | 24 | 28 | 0.389 | 0.353 | -2 | -1.4 | -13% | 0.727 |
| S1 | 18 | 24 | 28 | 0.440 | 0.411 | +2 | +2.5 | 22% | 0.625 |
| S6 | 16 | 26 | 26 | 0.422 | 0.388 | +0 | +0.6 | 5% | 1.000 |
| S5 | 19 | 25 | 25 | 0.447 | 0.414 | +3 | +3.5 | 31% | 0.250 |
| S5+S2 | 20 | 26 | 27 | 0.467 | 0.433 | +4 | +4.5 | 39% | 0.219 |
| S8a | 20 | 25 | 25 | 0.457 | 0.418 | +4 | +4.5 | 39% | 0.125 |
| S8a+S2 | 21 | 27 | 27 | 0.479 | 0.442 | +5 | +5.5 | 48% | 0.125 |
| S8b | 17 | 25 | 26 | 0.429 | 0.395 | +1 | +1.6 | 13% | 1.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 0 | 408 | 537900 | 0 | 181 / 204 (181) | 27 |
| S5+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 0 | 509 | 640579 | 0 | 181 / 204 (181) | 27 |
| S8a | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 0 | 408 | 781260 | 0 | 177 / 204 (177) | 27 |
| S8a+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 0 | 498 | 922954 | 0 | 177 / 204 (177) | 27 |
| S8b | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 0 | 464 | 1002799 | 0 |  | 27 |

Agent behaviour: S8b: 464 agent turns, 394 tool calls, 3 invalid actions, 47 forced submits, 0 unparsed final answers, forward/reversed top-1 agree in 10 of 35 bugs

### test (50 bugs; infrastructure failures 3; buggy method among the stored candidates in 22)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 12 | 21 | 22 | 0.325 | 0.289 | | | | |
| random ties, mean of 2000 (95% range) | 13.3 (10-16) | 20.1 | 21.0 | 0.331 | 0.298 | | | | |
| oracle tie-breaker (bound) | 21 | 22 | 22 | 0.427 | 0.376 | | | | |
| S0 | 12 | 21 | 22 | 0.325 | 0.289 | +0 | -1.3 | -17% | 1.000 |
| S0r | 15 | 19 | 21 | 0.345 | 0.314 | +3 | +1.7 | 22% | 0.375 |
| S1 | 14 | 21 | 21 | 0.343 | 0.302 | +2 | +0.7 | 9% | 0.625 |
| S6 | 13 | 19 | 22 | 0.326 | 0.296 | +1 | -0.3 | -4% | 1.000 |
| S5 | 15 | 20 | 22 | 0.353 | 0.326 | +3 | +1.7 | 22% | 0.375 |
| S5+S2 | 16 | 20 | 22 | 0.363 | 0.329 | +4 | +2.7 | 35% | 0.219 |
| S8a | 14 | 21 | 22 | 0.345 | 0.316 | +2 | +0.7 | 9% | 0.625 |
| S8a+S2 | 16 | 22 | 22 | 0.370 | 0.335 | +4 | +2.7 | 35% | 0.219 |
| S8b | 13 | 21 | 22 | 0.337 | 0.304 | +1 | -0.3 | -4% | 1.000 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 30 | 354 | 0 | 453262 | 101.1 | 151 / 177 (151) | 21 |
| S5+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 30 | 80 | 354 | 533515 | 13.2 | 151 / 177 (151) | 21 |
| S8a | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 30 | 354 | 0 | 695956 | 126.9 | 155 / 177 (155) | 21 |
| S8a+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 30 | 77 | 354 | 822138 | 14.5 | 155 / 177 (155) | 21 |
| S8b | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 30 | 396 | 0 | 839067 | 475.4 |  | 21 |

Agent behaviour: S8b: 396 agent turns, 336 tool calls, 1 invalid actions, 38 forced submits, 0 unparsed final answers, forward/reversed top-1 agree in 9 of 30 bugs

### all (100 bugs; infrastructure failures 6; buggy method among the stored candidates in 51)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 28 | 46 | 47 | 0.370 | 0.335 | | | | |
| random ties, mean of 2000 (95% range) | 28.8 (24-34) | 43.9 | 48.3 | 0.368 | 0.334 | | | | |
| oracle tie-breaker (bound) | 48 | 50 | 51 | 0.490 | 0.443 | | | | |
| S0 | 28 | 46 | 47 | 0.370 | 0.335 | +0 | -0.8 | -4% | 1.000 |
| S0r | 29 | 43 | 49 | 0.367 | 0.334 | +1 | +0.1 | 1% | 1.000 |
| S1 | 32 | 45 | 49 | 0.392 | 0.356 | +4 | +3.1 | 16% | 0.289 |
| S6 | 29 | 45 | 48 | 0.374 | 0.342 | +1 | +0.1 | 1% | 1.000 |
| S5 | 34 | 45 | 47 | 0.400 | 0.370 | +6 | +5.2 | 27% | 0.070 |
| S5+S2 | 36 | 46 | 49 | 0.415 | 0.381 | +8 | +7.2 | 37% | 0.039 |
| S8a | 34 | 46 | 47 | 0.401 | 0.367 | +6 | +5.2 | 27% | 0.070 |
| S8a+S2 | 37 | 49 | 49 | 0.424 | 0.389 | +9 | +8.2 | 43% | 0.022 |
| S8b | 30 | 46 | 48 | 0.383 | 0.350 | +2 | +1.1 | 6% | 0.625 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 65 | 354 | 408 | 991162 | 101.1 | 332 / 381 (332) | 48 |
| S5+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 65 | 80 | 863 | 1174094 | 13.2 | 332 / 381 (332) | 48 |
| S8a | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 65 | 354 | 408 | 1477216 | 126.9 | 332 / 381 (332) | 48 |
| S8a+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 65 | 77 | 852 | 1745092 | 14.5 | 332 / 381 (332) | 48 |
| S8b | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 65 | 396 | 464 | 1841866 | 475.4 |  | 48 |

Agent behaviour: S8b: 860 agent turns, 730 tool calls, 4 invalid actions, 85 forced submits, 0 unparsed final answers, forward/reversed top-1 agree in 19 of 65 bugs

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S6** = stack-trace and coverage tie-breaker (no model): on the stack first, shallower first, then share of failing tests that executed the method; **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score; **S8a** = S5 with a fixed evidence bundle from the failure context: failing tests, error output, stack frames and test code, plus per method its stack depth and coverage by failing tests (no loop); **S8a+S2** = S5+S2 with the S8a evidence bundle: evidence pairwise first, evidence log-prob score breaks its draws; **S8b** = agentic investigator: tool calls over the failure context and the candidates (step cap), then a ranking; run forward and reversed, combined by mean position

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
