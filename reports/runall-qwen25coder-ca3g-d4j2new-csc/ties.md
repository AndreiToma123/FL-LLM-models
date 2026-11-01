## Tie and selection analysis: runall-qwen25coder-ca3g-d4j2new-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 2)
* bugs with a ranking and a ground truth: 428
* buggy method present in the ranking (reachable by any tie-breaker): 236
* of those, buggy method shares its score with another method: 170
* Top-1 hits: 118; of these tied with another method: 54
* bugs whose highest score is shared by several methods: 293 of 428
* mean number of scored methods per bug: 15.5

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 118 | 186 | 206 |
| reversed review order | 112 | 179 | 202 |
| worst case (buggy method last in its tie) | 67 | 149 | 176 |
| best case (buggy method first in its tie) = oracle tie-breaker | 206 | 222 | 226 |
| random (mean of 2000 draws) | 112.4 | 184.1 | 203.5 |
| random, 95% range | 102-123 | 177-191 | 197-209 |

Reading: with the model's scores unchanged, Top-1 can range from 67 (worst) to 206 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 236 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 2617 |
| 2 | 5 |
| 3 | 95 |
| 4 | 60 |
| 5 | 1424 |
| 6 | 261 |
| 7 | 496 |
| 8 | 958 |
| 9 | 710 |
| 10 | 6 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 6 |
| 5 | 18 |
| 6 | 4 |
| 7 | 29 |
| 8 | 245 |
| 9 | 121 |
| 10 | 5 |
