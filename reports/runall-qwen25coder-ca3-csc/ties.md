## Tie and selection analysis: runall-qwen25coder-ca3-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 21)
* bugs with a ranking and a ground truth: 359
* buggy method present in the ranking (reachable by any tie-breaker): 259
* of those, buggy method shares its score with another method: 205
* Top-1 hits: 134; of these tied with another method: 83
* bugs whose highest score is shared by several methods: 280 of 359
* mean number of scored methods per bug: 19.7

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 134 | 206 | 234 |
| reversed review order | 97 | 180 | 210 |
| worst case (buggy method last in its tie) | 64 | 143 | 180 |
| best case (buggy method first in its tie) = oracle tie-breaker | 234 | 248 | 254 |
| random (mean of 2000 draws) | 113.9 | 191.7 | 222.8 |
| random, 95% range | 103-125 | 182-200 | 216-230 |

Reading: with the model's scores unchanged, Top-1 can range from 64 (worst) to 234 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 259 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 3138 |
| 2 | 3 |
| 3 | 47 |
| 4 | 21 |
| 5 | 1539 |
| 6 | 232 |
| 7 | 335 |
| 8 | 1264 |
| 9 | 489 |
| 10 | 4 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 5 | 5 |
| 6 | 2 |
| 7 | 18 |
| 8 | 247 |
| 9 | 85 |
| 10 | 2 |
