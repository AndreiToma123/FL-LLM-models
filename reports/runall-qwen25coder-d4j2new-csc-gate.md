## Gated escalation on runall-qwen25coder-d4j2new-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 | 110 | 167 | 0.316 | 0 | 0.0 | S0 419 | * |
| S0 > S6 | 110 | 167 | 0.316 | 0 | 0.0 | S0 165, S6 254 |  |
| S0 > S8a+S2 | 110 | 167 | 0.316 | 0 | 0.0 | S0 165, S8a+S2 254 |  |
| S0 > S6 > S8a+S2 | 110 | 167 | 0.316 | 0 | 0.0 | S0 165, S8a+S2 254 |  |

