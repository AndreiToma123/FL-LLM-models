## Gated escalation on runall-qwen25coder-ca3-d4j2new-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 125 | 193 | 0.368 | 0 | 0.0 | S0 92, S6 348 | * |
| S0 | 107 | 191 | 0.344 | 0 | 0.0 | S0 440 |  |
| S0 > S6 > S8a+S2 | 147 | 205 | 0.405 | 6415 | 14.4 | S0 92, S6 127, S8a+S2 221 | * |
| S0 > S8a+S2 | 142 | 208 | 0.401 | 9526 | 21.5 | S0 92, S8a+S2 348 |  |

