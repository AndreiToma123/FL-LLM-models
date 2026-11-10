## Tie and selection analysis: runall-qwen25coder-d4j2new-csc-r1

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 1)
* bugs with a ranking and a ground truth: 412
* buggy method present in the ranking (reachable by any tie-breaker): 185
* of those, buggy method shares its score with another method: 119
* Top-1 hits: 104; of these tied with another method: 40
* bugs whose highest score is shared by several methods: 245 of 412
* mean number of scored methods per bug: 5.3

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 104 | 163 | 177 |
| reversed review order | 110 | 166 | 175 |
| worst case (buggy method last in its tie) | 69 | 146 | 166 |
| best case (buggy method first in its tie) = oracle tie-breaker | 167 | 179 | 184 |
| random (mean of 2000 draws) | 107.3 | 164.7 | 176.3 |
| random, 95% range | 98-116 | 160-169 | 173-180 |

Reading: with the model's scores unchanged, Top-1 can range from 69 (worst) to 167 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 185 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0 | 468 |
| 2 | 1 |
| 3 | 12 |
| 4 | 10 |
| 5 | 424 |
| 6 | 104 |
| 7 | 255 |
| 8 | 623 |
| 9 | 301 |
| 10 | 4 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 0 | 11 |
| 4 | 2 |
| 5 | 20 |
| 6 | 9 |
| 7 | 31 |
| 8 | 222 |
| 9 | 114 |
| 10 | 3 |
