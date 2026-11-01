## Gated escalation on runall-qwen25coder-ca3-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 140 | 215 | 0.463 | 0 | 0.0 | S0 81, S6 286 | * |
| S0 | 134 | 206 | 0.449 | 0 | 0.0 | S0 367 |  |
| S0 > S6 > S8a+S2 | 156 | 223 | 0.492 | 5493 | 14.2 | S0 81, S6 73, S8a+S2 213 | * |
| S0 > S8a+S2 | 163 | 225 | 0.504 | 7234 | 18.6 | S0 81, S8a+S2 286 | * |

