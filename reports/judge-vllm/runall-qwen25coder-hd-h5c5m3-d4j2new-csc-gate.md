## Gated escalation on runall-qwen25coder-hd-h5c5m3-d4j2new-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 129 | 192 | 0.381 | 0 | 0.0 | S0 74, S6 365 | * |
| S0 | 119 | 188 | 0.365 | 0 | 0.0 | S0 439 |  |
| S0 > S6 > S8a+S2 | 149 | 209 | 0.418 | 13767 | 31.0 | S0 74, S6 126, S8a+S2 239 | * |
| S0 > S8a+S2 | 146 | 214 | 0.419 | 21146 | 47.6 | S0 74, S8a+S2 365 |  |

