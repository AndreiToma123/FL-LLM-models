## Gated escalation on runall-qwen25coder-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 136 | 193 | 0.422 | 0 | 0.0 | S0 146, S6 214 | * |
| S0 | 130 | 191 | 0.412 | 0 | 0.0 | S0 360 |  |
| S0 > S6 > S8a+S2 | 152 | 196 | 0.447 | 2286 | 5.9 | S0 146, S6 49, S8a+S2 165 | * |
| S0 > S8a+S2 | 152 | 195 | 0.446 | 2830 | 7.3 | S0 146, S8a+S2 214 |  |

