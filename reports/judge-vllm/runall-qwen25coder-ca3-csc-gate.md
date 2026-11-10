## Gated escalation on runall-qwen25coder-ca3-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 140 | 215 | 0.463 | 0 | 0.0 | S0 81, S6 286 | * |
| S0 | 134 | 206 | 0.449 | 0 | 0.0 | S0 367 |  |
| S0 > S6 > S8a+S2 | 164 | 224 | 0.506 | 5240 | 13.5 | S0 81, S6 73, S8a+S2 213 | * |
| S0 > S8a+S2 | 172 | 225 | 0.519 | 6947 | 17.9 | S0 81, S8a+S2 286 | * |

