## Tie and selection analysis: runall-qwen25coder-hd-h5c5m3-d4j2new-csc

Offline, no model calls. SoapFL sorts by score with a stable sort, so equal scores keep review order.

* bugs attempted: 444 (infrastructure failures: 4)
* bugs with a ranking and a ground truth: 426
* buggy method present in the ranking (reachable by any tie-breaker): 279
* of those, buggy method shares its score with another method: 240
* Top-1 hits: 119; of these tied with another method: 84
* bugs whose highest score is shared by several methods: 354 of 426
* mean number of scored methods per bug: 22.5

### Top-N under different orders inside tie groups (counts of bugs)

| Order inside tie groups | Top-1 | Top-3 | Top-5 |
|---|---:|---:|---:|
| actual (SoapFL review order) | 119 | 188 | 219 |
| reversed review order | 57 | 135 | 184 |
| worst case (buggy method last in its tie) | 36 | 99 | 141 |
| best case (buggy method first in its tie) = oracle tie-breaker | 223 | 235 | 241 |
| random (mean of 2000 draws) | 81.6 | 164.0 | 202.1 |
| random, 95% range | 71-93 | 153-175 | 193-211 |

Reading: with the model's scores unchanged, Top-1 can range from 36 (worst) to 223 (best) out of 444 attempted bugs, only by reordering equal scores. Reachable ceiling for any selection rule on this run: 279 (buggy method scored at all).

### Score scale actually used (all scored methods)

| Score | Methods |
|---:|---:|
| 0.0 | 1421 |
| 1.0 | 2 |
| 2.0 | 15 |
| 3.0 | 610 |
| 4.0 | 209 |
| 5.0 | 2217 |
| 6.0 | 425 |
| 7.0 | 1140 |
| 8.0 | 2307 |
| 9.0 | 1193 |
| 10.0 | 32 |

### Highest score per bug

| Top score | Bugs |
|---:|---:|
| 5.0 | 2 |
| 6.0 | 2 |
| 7.0 | 18 |
| 8.0 | 240 |
| 9.0 | 146 |
| 10.0 | 18 |
