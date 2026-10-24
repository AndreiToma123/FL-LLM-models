## Selection replay on run100-qwen25coder (100 bugs, seed 0)

No new model calls for S0/S0r/S1*. Selectors only reorder methods inside the source run's ties.

### dev (50 bugs; infrastructure failures 3; buggy method among the stored candidates in 29)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 16 | 25 | 25 | 0.414 | 0.381 | | | | |
| random ties, mean of 2000 (95% range) | 15.5 (12-19) | 23.9 | 27.2 | 0.404 | 0.369 | | | | |
| oracle tie-breaker (bound) | 27 | 28 | 29 | 0.554 | 0.511 | | | | |
| S0 | 16 | 25 | 25 | 0.414 | 0.381 | +0 | +0.6 | 5% | 1.000 |
| S0r | 14 | 24 | 28 | 0.389 | 0.353 | -2 | -1.4 | -13% | 0.727 |
| S1 | 18 | 24 | 28 | 0.440 | 0.411 | +2 | +2.5 | 22% | 0.625 |
| S1-body | 17 | 26 | 28 | 0.437 | 0.401 | +1 | +1.6 | 13% | 1.000 |

### test (50 bugs; infrastructure failures 3; buggy method among the stored candidates in 22)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 12 | 21 | 22 | 0.325 | 0.289 | | | | |
| random ties, mean of 2000 (95% range) | 13.3 (10-16) | 20.1 | 21.0 | 0.331 | 0.298 | | | | |
| oracle tie-breaker (bound) | 21 | 22 | 22 | 0.427 | 0.376 | | | | |
| S0 | 12 | 21 | 22 | 0.325 | 0.289 | +0 | -1.3 | -17% | 1.000 |
| S0r | 15 | 19 | 21 | 0.345 | 0.314 | +3 | +1.7 | 22% | 0.375 |
| S1 | 14 | 21 | 21 | 0.343 | 0.302 | +2 | +0.7 | 9% | 0.625 |
| S1-body | 14 | 21 | 21 | 0.347 | 0.319 | +2 | +0.7 | 9% | 0.727 |

### all (100 bugs; infrastructure failures 6; buggy method among the stored candidates in 51)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 28 | 46 | 47 | 0.370 | 0.335 | | | | |
| random ties, mean of 2000 (95% range) | 28.8 (24-34) | 43.9 | 48.3 | 0.368 | 0.334 | | | | |
| oracle tie-breaker (bound) | 48 | 50 | 51 | 0.490 | 0.443 | | | | |
| S0 | 28 | 46 | 47 | 0.370 | 0.335 | +0 | -0.8 | -4% | 1.000 |
| S0r | 29 | 43 | 49 | 0.367 | 0.334 | +1 | +0.1 | 1% | 1.000 |
| S1 | 32 | 45 | 49 | 0.392 | 0.356 | +4 | +3.1 | 16% | 0.289 |
| S1-body | 31 | 47 | 49 | 0.392 | 0.360 | +3 | +2.1 | 11% | 0.607 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S1-body** = ties broken by TF-IDF similarity of the method (name, doc, code) to the failure analysis only

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
