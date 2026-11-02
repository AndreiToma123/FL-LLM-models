## Tie and selection analysis: runall-qwen25coder-hd-h5c5m3-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 43)
* bugs with a ranking and a ground truth: 338
* buggy method present in the ranking (reachable by any tie-breaker): 238
* of those, buggy method shares its score with another method: 194
* Top-1 hits: 118; of these tied with another method: 83
* bugs whose highest score is shared by several methods: 263 of 338
* mean number of scored methods per bug: 21.2

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 118 | 185 | 200 |
| reversed review order | 65 | 150 | 174 |
| worst case (buggy method last in its tie) | 42 | 123 | 159 |
| best case (buggy method first in its tie) = oracle tie-breaker | 181 | 204 | 209 |
| random (mean of 2000 draws) | 85.8 | 164.2 | 191.6 |
| random, 95% range | 76-96 | 156-172 | 185-198 |

Reading: with the model's scores unchanged, Top-1 can range from 42 (worst) to 181 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 238 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0.0 | 1517 |
| 2.0 | 15 |
| 3.0 | 198 |
| 4.0 | 65 |
| 5.0 | 1973 |
| 6.0 | 301 |
| 7.0 | 373 |
| 8.0 | 2104 |
| 9.0 | 585 |
| 10.0 | 26 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 5.0 | 4 |
| 6.0 | 2 |
| 7.0 | 9 |
| 8.0 | 224 |
| 9.0 | 77 |
| 10.0 | 22 |
