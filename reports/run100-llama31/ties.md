## Tie and selection analysis: run100-llama31

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 100 (infrastructure failures: 7)
* bugs with a ranking and a ground truth: 88
* buggy method present in the ranking (reachable by any tie-breaker): 48
* of those, buggy method shares its score with another method: 41
* Top-1 hits: 14; of these tied with another method: 8
* bugs whose highest score is shared by several methods: 74 of 88
* mean number of scored methods per bug: 5.2

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 14 | 38 | 44 |
| reversed review order | 23 | 42 | 46 |
| worst case (buggy method last in its tie) | 8 | 25 | 38 |
| best case (buggy method first in its tie) = oracle tie-breaker | 46 | 47 | 48 |
| random (mean of 2000 draws) | 19.6 | 37.8 | 44.6 |
| random, 95% range | 15-25 | 33-42 | 42-47 |

Reading: with the model's scores unchanged, Top-1 can range from 8 (worst) to 46 (best) out of 100 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 48 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 2 | 29 |
| 6 | 59 |
| 8 | 40 |
| 9 | 332 |
| 10 | 1 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 8 | 5 |
| 9 | 82 |
| 10 | 1 |
