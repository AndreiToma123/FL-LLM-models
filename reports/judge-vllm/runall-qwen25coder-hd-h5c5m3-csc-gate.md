## Gated escalation on runall-qwen25coder-hd-h5c5m3-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 | 127 | 196 | 0.424 | 0 | 0.0 | S0 369 | * |
| S0 > S6 | 122 | 197 | 0.417 | 0 | 0.0 | S0 79, S6 290 |  |
| S0 > S6 > S8a+S2 | 142 | 209 | 0.457 | 11479 | 29.6 | S0 79, S6 72, S8a+S2 218 | * |
| S0 > S8a+S2 | 146 | 208 | 0.464 | 15234 | 39.3 | S0 79, S8a+S2 290 | * |

