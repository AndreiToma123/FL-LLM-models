## Gated escalation on runall-qwen25coder-d4j2new-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 125 | 169 | 0.336 | 0 | 0.0 | S0 165, S6 254 | * |
| S0 | 110 | 167 | 0.316 | 0 | 0.0 | S0 419 |  |
| S0 > S6 > S8a+S2 | 141 | 168 | 0.354 | 2518 | 5.7 | S0 165, S6 89, S8a+S2 165 | * |
| S0 > S8a+S2 | 134 | 170 | 0.348 | 3533 | 8.0 | S0 165, S8a+S2 254 |  |

