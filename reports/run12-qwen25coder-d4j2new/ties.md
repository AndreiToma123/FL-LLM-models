## Tie and selection analysis: run12-qwen25coder-d4j2new

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 12 (infrastructure failures: 0)
* bugs with a ranking and a ground truth: 12
* buggy method present in the ranking (reachable by any tie-breaker): 6
* of those, buggy method shares its score with another method: 5
* Top-1 hits: 4; of these tied with another method: 3
* bugs whose highest score is shared by several methods: 9 of 12
* mean number of scored methods per bug: 4.3

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 4 | 6 | 6 |
| reversed review order | 2 | 6 | 6 |
| worst case (buggy method last in its tie) | 1 | 6 | 6 |
| best case (buggy method first in its tie) = oracle tie-breaker | 6 | 6 | 6 |
| random (mean of 2000 draws) | 3.2 | 6.0 | 6.0 |
| random, 95% range | 1-5 | 6-6 | 6-6 |

Reading: with the model's scores unchanged, Top-1 can range from 1 (worst) to 6 (best) out of 12 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 6 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 11 |
| 5 | 9 |
| 7 | 1 |
| 8 | 31 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 5 | 1 |
| 8 | 11 |
