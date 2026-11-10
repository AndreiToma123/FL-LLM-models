## Gated escalation on runall-qwen25coder-d4j2new-csc-r1 (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 116 | 165 | 0.320 | 0 | 0.0 | S0 169, S6 254 | * |
| S0 | 104 | 163 | 0.303 | 0 | 0.0 | S0 423 |  |
| S0 > S6 > S8a+S2 | 139 | 168 | 0.350 | 2433 | 5.5 | S0 169, S6 83, S8a+S2 171 | * |
| S0 > S8a+S2 | 138 | 170 | 0.349 | 3233 | 7.3 | S0 169, S8a+S2 254 |  |

