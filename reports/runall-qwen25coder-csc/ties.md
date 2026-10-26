## Tie and selection analysis: runall-qwen25coder-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 17)
* bugs with a ranking and a ground truth: 352
* buggy method present in the ranking (reachable by any tie-breaker): 207
* of those, buggy method shares its score with another method: 132
* Top-1 hits: 130; of these tied with another method: 61
* bugs whose highest score is shared by several methods: 210 of 352
* mean number of scored methods per bug: 5.1

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 130 | 191 | 199 |
| reversed review order | 109 | 186 | 197 |
| worst case (buggy method last in its tie) | 84 | 162 | 187 |
| best case (buggy method first in its tie) = oracle tie-breaker | 187 | 206 | 207 |
| random (mean of 2000 draws) | 121.1 | 187.1 | 199.1 |
| random, 95% range | 112-131 | 181-193 | 195-203 |

Reading: with the model's scores unchanged, Top-1 can range from 84 (worst) to 187 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 207 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 324 |
| 2 | 1 |
| 3 | 31 |
| 4 | 3 |
| 5 | 330 |
| 6 | 65 |
| 7 | 129 |
| 8 | 682 |
| 9 | 233 |
| 10 | 7 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 9 |
| 5 | 17 |
| 6 | 6 |
| 7 | 15 |
| 8 | 220 |
| 9 | 80 |
| 10 | 5 |
