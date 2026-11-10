## Gated escalation on runall-qwen25coder-ca3g-d4j2new-csc-r1 (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 124 | 178 | 0.354 | 0 | 0.0 | S0 120, S6 321 | * |
| S0 | 111 | 177 | 0.335 | 0 | 0.0 | S0 441 |  |
| S0 > S6 > S8a+S2 | 148 | 187 | 0.388 | 4562 | 10.3 | S0 120, S6 123, S8a+S2 198 | * |
| S0 > S8a+S2 | 143 | 187 | 0.381 | 6677 | 15.0 | S0 120, S8a+S2 321 |  |

