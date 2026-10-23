## Tie and selection analysis: run10-qwen25coder-hd-h5c5

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 10 (infrastructure failures: 2)
* bugs with a ranking and a ground truth: 8
* buggy method present in the ranking (reachable by any tie-breaker): 6
* of those, buggy method shares its score with another method: 5
* Top-1 hits: 1; of these tied with another method: 0
* bugs whose highest score is shared by several methods: 4 of 8
* mean number of scored methods per bug: 79.6

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 1 | 1 | 5 |
| reversed review order | 1 | 2 | 3 |
| worst case (buggy method last in its tie) | 1 | 1 | 2 |
| best case (buggy method first in its tie) = oracle tie-breaker | 1 | 3 | 5 |
| random (mean of 2000 draws) | 1.0 | 1.6 | 3.0 |
| random, 95% range | 1-1 | 1-3 | 2-4 |

Reading: with the model's scores unchanged, Top-1 can range from 1 (worst) to 1 (best) out of 10 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 6 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0.0 | 126 |
| 2.0 | 2 |
| 5.0 | 218 |
| 7.0 | 1 |
| 8.0 | 276 |
| 9.0 | 5 |
| 10.0 | 9 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 8.0 | 3 |
| 10.0 | 5 |
