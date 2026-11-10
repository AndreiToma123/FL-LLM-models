## Tie and selection analysis: runall-qwen25coder-ca3-d4j2new-csc-r1

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 2)
* bugs with a ranking and a ground truth: 428
* buggy method present in the ranking (reachable by any tie-breaker): 252
* of those, buggy method shares its score with another method: 201
* Top-1 hits: 117; of these tied with another method: 67
* bugs whose highest score is shared by several methods: 330 of 428
* mean number of scored methods per bug: 20.3

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 117 | 189 | 215 |
| reversed review order | 90 | 170 | 205 |
| worst case (buggy method last in its tie) | 54 | 121 | 162 |
| best case (buggy method first in its tie) = oracle tie-breaker | 224 | 237 | 243 |
| random (mean of 2000 draws) | 101.9 | 176.8 | 209.6 |
| random, 95% range | 91-113 | 167-186 | 202-217 |

Reading: with the model's scores unchanged, Top-1 can range from 54 (worst) to 224 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 252 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 3633 |
| 2 | 3 |
| 3 | 32 |
| 4 | 89 |
| 5 | 1912 |
| 6 | 376 |
| 7 | 670 |
| 8 | 1141 |
| 9 | 827 |
| 10 | 5 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 4 |
| 4 | 1 |
| 5 | 9 |
| 6 | 2 |
| 7 | 33 |
| 8 | 250 |
| 9 | 125 |
| 10 | 4 |
