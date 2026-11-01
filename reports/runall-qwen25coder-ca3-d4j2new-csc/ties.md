## Tie and selection analysis: runall-qwen25coder-ca3-d4j2new-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 3)
* bugs with a ranking and a ground truth: 428
* buggy method present in the ranking (reachable by any tie-breaker): 253
* of those, buggy method shares its score with another method: 201
* Top-1 hits: 107; of these tied with another method: 60
* bugs whose highest score is shared by several methods: 338 of 428
* mean number of scored methods per bug: 20.1

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 107 | 191 | 213 |
| reversed review order | 84 | 153 | 199 |
| worst case (buggy method last in its tie) | 51 | 108 | 153 |
| best case (buggy method first in its tie) = oracle tie-breaker | 222 | 233 | 243 |
| random (mean of 2000 draws) | 96.1 | 169.2 | 205.2 |
| random, 95% range | 86-107 | 159-179 | 197-213 |

Reading: with the model's scores unchanged, Top-1 can range from 51 (worst) to 222 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 253 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 3481 |
| 2 | 4 |
| 3 | 124 |
| 4 | 40 |
| 5 | 1880 |
| 6 | 413 |
| 7 | 624 |
| 8 | 1199 |
| 9 | 850 |
| 10 | 5 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 3 |
| 3 | 1 |
| 5 | 14 |
| 6 | 4 |
| 7 | 35 |
| 8 | 247 |
| 9 | 120 |
| 10 | 4 |
