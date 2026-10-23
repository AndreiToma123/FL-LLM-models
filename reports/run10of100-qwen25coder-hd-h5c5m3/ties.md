## Tie and selection analysis: run10of100-qwen25coder-hd-h5c5m3

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 10 (infrastructure failures: 1)
* bugs with a ranking and a ground truth: 9
* buggy method present in the ranking (reachable by any tie-breaker): 7
* of those, buggy method shares its score with another method: 7
* Top-1 hits: 0; of these tied with another method: 0
* bugs whose highest score is shared by several methods: 8 of 9
* mean number of scored methods per bug: 19.4

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 0 | 2 | 3 |
| reversed review order | 1 | 1 | 1 |
| worst case (buggy method last in its tie) | 0 | 1 | 1 |
| best case (buggy method first in its tie) = oracle tie-breaker | 3 | 3 | 3 |
| random (mean of 2000 draws) | 0.5 | 1.7 | 2.1 |
| random, 95% range | 0-2 | 1-3 | 1-3 |

Reading: with the model's scores unchanged, Top-1 can range from 0 (worst) to 3 (best) out of 10 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 7 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0.0 | 28 |
| 2.0 | 1 |
| 5.0 | 29 |
| 7.0 | 1 |
| 8.0 | 113 |
| 10.0 | 3 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 8.0 | 7 |
| 10.0 | 2 |
