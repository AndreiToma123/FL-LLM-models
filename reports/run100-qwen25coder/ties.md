## Tie and selection analysis: run100-qwen25coder

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 100 (infrastructure failures: 6)
* bugs with a ranking and a ground truth: 92
* buggy method present in the ranking (reachable by any tie-breaker): 51
* of those, buggy method shares its score with another method: 35
* Top-1 hits: 28; of these tied with another method: 13
* bugs whose highest score is shared by several methods: 64 of 92
* mean number of scored methods per bug: 4.2

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 28 | 46 | 47 |
| reversed review order | 27 | 43 | 49 |
| worst case (buggy method last in its tie) | 19 | 36 | 44 |
| best case (buggy method first in its tie) = oracle tie-breaker | 48 | 50 | 51 |
| random (mean of 2000 draws) | 28.8 | 43.9 | 48.3 |
| random, 95% range | 24-34 | 41-47 | 46-50 |

Reading: with the model's scores unchanged, Top-1 can range from 19 (worst) to 48 (best) out of 100 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 51 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 73 |
| 2 | 2 |
| 5 | 52 |
| 7 | 7 |
| 8 | 252 |
| 10 | 4 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 1 |
| 5 | 1 |
| 7 | 2 |
| 8 | 85 |
| 10 | 3 |
