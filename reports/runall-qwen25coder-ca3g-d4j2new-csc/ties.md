## Tie and selection analysis: runall-qwen25coder-ca3g-d4j2new-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 444)
* bugs with a ranking and a ground truth: 0
* buggy method present in the ranking (reachable by any tie-breaker): 0
* of those, buggy method shares its score with another method: 0
* Top-1 hits: 0; of these tied with another method: 0
* bugs whose highest score is shared by several methods: 0 of 0
* mean number of scored methods per bug: 0.0

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 0 | 0 | 0 |
| reversed review order | 0 | 0 | 0 |
| worst case (buggy method last in its tie) | 0 | 0 | 0 |
| best case (buggy method first in its tie) = oracle tie-breaker | 0 | 0 | 0 |
| random (mean of 2000 draws) | 0.0 | 0.0 | 0.0 |
| random, 95% range | 0-0 | 0-0 | 0-0 |

Reading: with the model's scores unchanged, Top-1 can range from 0 (worst) to 0 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 0 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|

### Highest score per bug

| Top score | Bugs |
|---:|---:|
