## Tie and selection analysis: runall-qwen25coder-ca3g-d4j2new-csc-r1

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 2)
* bugs with a ranking and a ground truth: 428
* buggy method present in the ranking (reachable by any tie-breaker): 234
* of those, buggy method shares its score with another method: 174
* Top-1 hits: 111; of these tied with another method: 54
* bugs whose highest score is shared by several methods: 310 of 428
* mean number of scored methods per bug: 15.8

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 111 | 177 | 202 |
| reversed review order | 109 | 179 | 200 |
| worst case (buggy method last in its tie) | 61 | 144 | 176 |
| best case (buggy method first in its tie) = oracle tie-breaker | 203 | 215 | 227 |
| random (mean of 2000 draws) | 108.6 | 177.6 | 200.5 |
| random, 95% range | 99-119 | 170-185 | 194-207 |

Reading: with the model's scores unchanged, Top-1 can range from 61 (worst) to 203 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 234 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 2681 |
| 2 | 2 |
| 3 | 87 |
| 4 | 68 |
| 5 | 1455 |
| 6 | 336 |
| 7 | 498 |
| 8 | 959 |
| 9 | 679 |
| 10 | 4 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 5 |
| 4 | 2 |
| 5 | 17 |
| 6 | 6 |
| 7 | 21 |
| 8 | 247 |
| 9 | 126 |
| 10 | 4 |
