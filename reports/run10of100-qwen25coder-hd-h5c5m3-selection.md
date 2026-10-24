## Selection replay on run10of100-qwen25coder-hd-h5c5m3 (10 bugs, seed 0)

No new model calls for S0/S0r/S1*. Selectors only reorder methods inside the source run's ties.

### all (10 bugs; infrastructure failures 1; buggy method among the stored candidates in 7)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 0 | 2 | 3 | 0.121 | 0.112 | | | | |
| random ties, mean of 2000 (95% range) | 0.5 (0-2) | 1.7 | 2.1 | 0.151 | 0.142 | | | | |
| oracle tie-breaker (bound) | 3 | 3 | 3 | 0.333 | 0.323 | | | | |
| S0 | 0 | 2 | 3 | 0.121 | 0.112 | +0 | -0.5 | -22% | 1.000 |
| S0r | 2 | 3 | 3 | 0.278 | 0.270 | +2 | +1.5 | 59% | 0.500 |
| S1 | 0 | 1 | 3 | 0.108 | 0.098 | +0 | -0.5 | -22% | 1.000 |
| S1-body | 1 | 2 | 3 | 0.183 | 0.174 | +1 | +0.5 | 19% | 1.000 |

Selectors: **S0** = source run's own order (ties in review order); **S0r** = random order inside ties (one seeded draw; the expectation is reported separately); **S1** = ties broken by lexical evidence: method named in the failure analysis, then name overlap, then TF-IDF similarity of the method to the failure analysis; **S1-body** = ties broken by TF-IDF similarity of the method (name, doc, code) to the failure analysis only

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
