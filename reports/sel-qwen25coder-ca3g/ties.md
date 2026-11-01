## Tie and selection analysis: sel-qwen25coder-ca3g

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 3 (infrastructure failures: 0)
* bugs with a ranking and a ground truth: 3
* buggy method present in the ranking (reachable by any tie-breaker): 1
* of those, buggy method shares its score with another method: 0
* Top-1 hits: 1; of these tied with another method: 0
* bugs whose highest score is shared by several methods: 2 of 3
* mean number of scored methods per bug: 2.3

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 1 | 1 | 1 |
| reversed review order | 1 | 1 | 1 |
| worst case (buggy method last in its tie) | 1 | 1 | 1 |
| best case (buggy method first in its tie) = oracle tie-breaker | 1 | 1 | 1 |
| random (mean of 2000 draws) | 1.0 | 1.0 | 1.0 |
| random, 95% range | 1-1 | 1-1 | 1-1 |

Reading: with the model's scores unchanged, Top-1 can range from 1 (worst) to 1 (best) out of 3 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 1 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 5 | 1 |
| 8 | 6 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 8 | 3 |
