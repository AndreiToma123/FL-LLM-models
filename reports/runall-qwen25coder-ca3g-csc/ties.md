## Tie and selection analysis: runall-qwen25coder-ca3g-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 19)
* bugs with a ranking and a ground truth: 360
* buggy method present in the ranking (reachable by any tie-breaker): 240
* of those, buggy method shares its score with another method: 169
* Top-1 hits: 124; of these tied with another method: 58
* bugs whose highest score is shared by several methods: 249 of 360
* mean number of scored methods per bug: 10.9

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 124 | 200 | 215 |
| reversed review order | 117 | 194 | 215 |
| worst case (buggy method last in its tie) | 78 | 160 | 190 |
| best case (buggy method first in its tie) = oracle tie-breaker | 216 | 229 | 230 |
| random (mean of 2000 draws) | 121.4 | 195.7 | 214.3 |
| random, 95% range | 112-131 | 188-203 | 209-220 |

Reading: with the model's scores unchanged, Top-1 can range from 78 (worst) to 216 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 240 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 1321 |
| 2 | 2 |
| 3 | 7 |
| 4 | 11 |
| 5 | 865 |
| 6 | 104 |
| 7 | 251 |
| 8 | 1043 |
| 9 | 324 |
| 10 | 4 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 1 |
| 5 | 8 |
| 6 | 3 |
| 7 | 13 |
| 8 | 254 |
| 9 | 77 |
| 10 | 4 |
