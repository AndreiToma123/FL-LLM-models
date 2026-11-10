## Tie and selection analysis: runall-qwen25coder-ca3g-csc-r1

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 21)
* bugs with a ranking and a ground truth: 357
* buggy method present in the ranking (reachable by any tie-breaker): 236
* of those, buggy method shares its score with another method: 167
* Top-1 hits: 132; of these tied with another method: 67
* bugs whose highest score is shared by several methods: 247 of 357
* mean number of scored methods per bug: 10.7

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 132 | 203 | 217 |
| reversed review order | 123 | 198 | 213 |
| worst case (buggy method last in its tie) | 79 | 162 | 193 |
| best case (buggy method first in its tie) = oracle tie-breaker | 217 | 230 | 233 |
| random (mean of 2000 draws) | 124.7 | 198.4 | 216.2 |
| random, 95% range | 114-135 | 192-206 | 211-222 |

Reading: with the model's scores unchanged, Top-1 can range from 79 (worst) to 217 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 236 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 1187 |
| 2 | 2 |
| 3 | 6 |
| 4 | 23 |
| 5 | 941 |
| 6 | 133 |
| 7 | 224 |
| 8 | 980 |
| 9 | 310 |
| 10 | 4 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 4 | 1 |
| 5 | 12 |
| 6 | 4 |
| 7 | 13 |
| 8 | 244 |
| 9 | 80 |
| 10 | 3 |
