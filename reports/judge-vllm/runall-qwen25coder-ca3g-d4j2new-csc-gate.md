## Gated escalation on runall-qwen25coder-ca3g-d4j2new-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 127 | 194 | 0.366 | 0 | 0.0 | S0 137, S6 304 | * |
| S0 | 118 | 186 | 0.351 | 0 | 0.0 | S0 441 |  |
| S0 > S6 > S8a+S2 | 146 | 197 | 0.394 | 5255 | 11.8 | S0 137, S6 115, S8a+S2 189 | * |
| S0 > S8a+S2 | 145 | 196 | 0.392 | 7274 | 16.4 | S0 137, S8a+S2 304 |  |

