## Tie and selection analysis: runall-qwen25coder-hd-h5c5m3-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 388 (infrastructure failures: 19)
* bugs with a ranking and a ground truth: 361
* buggy method present in the ranking (reachable by any tie-breaker): 253
* of those, buggy method shares its score with another method: 208
* Top-1 hits: 127; of these tied with another method: 91
* bugs whose highest score is shared by several methods: 283 of 361
* mean number of scored methods per bug: 20.9

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 127 | 196 | 213 |
| reversed review order | 68 | 157 | 183 |
| worst case (buggy method last in its tie) | 43 | 128 | 167 |
| best case (buggy method first in its tie) = oracle tie-breaker | 193 | 216 | 222 |
| random (mean of 2000 draws) | 90.1 | 173.2 | 202.7 |
| random, 95% range | 80-100 | 165-182 | 196-209 |

Reading: with the model's scores unchanged, Top-1 can range from 43 (worst) to 193 (best) out of 388 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 253 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0.0 | 1568 |
| 2.0 | 15 |
| 3.0 | 231 |
| 4.0 | 69 |
| 5.0 | 2106 |
| 6.0 | 310 |
| 7.0 | 434 |
| 8.0 | 2179 |
| 9.0 | 622 |
| 10.0 | 27 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 5.0 | 6 |
| 6.0 | 2 |
| 7.0 | 12 |
| 8.0 | 235 |
| 9.0 | 83 |
| 10.0 | 23 |
