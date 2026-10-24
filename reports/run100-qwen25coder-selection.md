## Selection replay on run100-qwen25coder (100 bugs, seed 0)

S0/S0r/S1* make no model calls and only reorder inside the source run's ties. Model-based selectors re-rank a shortlist; with shortlist top-k they may cross score tiers, so the tie oracle is not their bound (see 'Top-1 reachable in shortlist').

### dev (50 bugs; infrastructure failures 3; buggy method among the stored candidates in 29)

| Selector | Top-1 | Top-3 | Top-5 | MRR | MAP | Top-1 vs source | vs random ties | oracle gap recovered | McNemar p (Top-1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source order (S0) | 16 | 25 | 25 | 0.414 | 0.381 | | | | |
| random ties, mean of 2000 (95% range) | 15.5 (12-19) | 23.9 | 27.2 | 0.404 | 0.369 | | | | |
| oracle tie-breaker (bound) | 27 | 28 | 29 | 0.554 | 0.511 | | | | |
| S5 | 19 | 25 | 25 | 0.447 | 0.414 | +3 | +3.5 | 31% | 0.250 |
| S5+S2 | 20 | 26 | 27 | 0.467 | 0.433 | +4 | +4.5 | 39% | 0.219 |

Model-based selectors, cost and reach on this part:

| Selector | judge model | shortlist (K) | bugs judged | new calls | cached | tokens | GPU seconds | pairs drawn / pairs (position-inconsistent) | Top-1 reachable in shortlist |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 299 | 109 | 537900 | 121.2 | 181 / 204 (181) | 27 |
| S5+S2 | soapfl-qwen2-5-coder-latest-c16384:latest | top-tie (8) | 35 | 77 | 432 | 640579 | 19.5 | 181 / 204 (181) | 27 |

Selectors: **S5** = pairwise judge on the shortlist, both orders, Copeland score; remaining ties keep source order; **S5+S2** = pairwise judge first (Copeland); candidates still tied are ordered by the S2 expected score

A Top-1 inside the random-ties 95% range is not evidence of a better selector.
Test part hidden: choose on dev, then run once with --reveal-test.
