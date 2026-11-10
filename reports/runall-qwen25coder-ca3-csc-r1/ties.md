## Tie and selection analysis: runall-qwen25coder-ca3-csc-r1

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 19)
* bugs with a ranking and a ground truth: 361
* buggy method present in the ranking (reachable by any tie-breaker): 257
* of those, buggy method shares its score with another method: 206
* Top-1 hits: 133; of these tied with another method: 85
* bugs whose highest score is shared by several methods: 269 of 361
* mean number of scored methods per bug: 19.4

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 133 | 210 | 229 |
| reversed review order | 97 | 177 | 213 |
| worst case (buggy method last in its tie) | 61 | 139 | 185 |
| best case (buggy method first in its tie) = oracle tie-breaker | 233 | 251 | 255 |
| random (mean of 2000 draws) | 111.7 | 191.9 | 221.9 |
| random, 95% range | 100-123 | 182-201 | 215-230 |

Reading: with the model's scores unchanged, Top-1 can range from 61 (worst) to 233 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 257 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 2905 |
| 2 | 3 |
| 3 | 55 |
| 4 | 22 |
| 5 | 1676 |
| 6 | 297 |
| 7 | 337 |
| 8 | 1301 |
| 9 | 413 |
| 10 | 6 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 3 | 1 |
| 5 | 8 |
| 6 | 4 |
| 7 | 13 |
| 8 | 251 |
| 9 | 80 |
| 10 | 4 |
