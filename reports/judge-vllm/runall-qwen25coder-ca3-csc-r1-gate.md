## Gated escalation on runall-qwen25coder-ca3-csc-r1 (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 135 | 212 | 0.459 | 0 | 0.0 | S0 93, S6 276 | * |
| S0 | 133 | 210 | 0.452 | 0 | 0.0 | S0 369 |  |
| S0 > S6 > S8a+S2 | 161 | 226 | 0.504 | 5218 | 13.4 | S0 93, S6 73, S8a+S2 203 | * |
| S0 > S8a+S2 | 170 | 227 | 0.518 | 6801 | 17.5 | S0 93, S8a+S2 276 | * |

