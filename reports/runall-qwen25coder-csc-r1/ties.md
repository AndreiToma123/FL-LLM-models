## Tie and selection analysis: runall-qwen25coder-csc-r1

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 17)
* bugs with a ranking and a ground truth: 351
* buggy method present in the ranking (reachable by any tie-breaker): 206
* of those, buggy method shares its score with another method: 133
* Top-1 hits: 124; of these tied with another method: 57
* bugs whose highest score is shared by several methods: 229 of 351
* mean number of scored methods per bug: 5.3

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 124 | 190 | 199 |
| reversed review order | 118 | 183 | 199 |
| worst case (buggy method last in its tie) | 82 | 162 | 188 |
| best case (buggy method first in its tie) = oracle tie-breaker | 192 | 203 | 205 |
| random (mean of 2000 draws) | 122.8 | 186.2 | 199.1 |
| random, 95% range | 114-132 | 181-192 | 195-202 |

Reading: with the model's scores unchanged, Top-1 can range from 82 (worst) to 192 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 206 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 304 |
| 2 | 2 |
| 3 | 20 |
| 4 | 9 |
| 5 | 373 |
| 6 | 69 |
| 7 | 125 |
| 8 | 730 |
| 9 | 210 |
| 10 | 3 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 2 |
| 3 | 1 |
| 5 | 22 |
| 6 | 6 |
| 7 | 16 |
| 8 | 223 |
| 9 | 79 |
| 10 | 2 |
