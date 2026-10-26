## Tie and selection analysis: runall-qwen25coder-d4j2new-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 2)
* bugs with a ranking and a ground truth: 407
* buggy method present in the ranking (reachable by any tie-breaker): 189
* of those, buggy method shares its score with another method: 127
* Top-1 hits: 110; of these tied with another method: 49
* bugs whose highest score is shared by several methods: 247 of 407
* mean number of scored methods per bug: 5.1

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 110 | 167 | 178 |
| reversed review order | 109 | 170 | 182 |
| worst case (buggy method last in its tie) | 66 | 149 | 166 |
| best case (buggy method first in its tie) = oracle tie-breaker | 171 | 185 | 186 |
| random (mean of 2000 draws) | 108.1 | 168.6 | 179.8 |
| random, 95% range | 99-117 | 163-174 | 176-183 |

Reading: with the model's scores unchanged, Top-1 can range from 66 (worst) to 171 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 189 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 475 |
| 2 | 2 |
| 3 | 5 |
| 4 | 7 |
| 5 | 336 |
| 6 | 97 |
| 7 | 221 |
| 8 | 610 |
| 9 | 312 |
| 10 | 2 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 10 |
| 4 | 3 |
| 5 | 21 |
| 6 | 6 |
| 7 | 34 |
| 8 | 219 |
| 9 | 112 |
| 10 | 2 |
