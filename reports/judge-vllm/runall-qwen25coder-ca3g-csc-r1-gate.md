## Gated escalation on runall-qwen25coder-ca3g-csc-r1 (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 138 | 209 | 0.447 | 0 | 0.0 | S0 113, S6 252 | * |
| S0 | 132 | 203 | 0.433 | 0 | 0.0 | S0 365 |  |
| S0 > S6 > S8a+S2 | 155 | 218 | 0.478 | 3256 | 8.4 | S0 113, S6 73, S8a+S2 179 | * |
| S0 > S8a+S2 | 160 | 217 | 0.484 | 4734 | 12.2 | S0 113, S8a+S2 252 | * |

