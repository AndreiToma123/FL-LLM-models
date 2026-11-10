## Gated escalation on runall-qwen25coder-csc-r1 (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 138 | 194 | 0.424 | 0 | 0.0 | S0 125, S6 234 | * |
| S0 | 124 | 190 | 0.402 | 0 | 0.0 | S0 359 |  |
| S0 > S6 > S8a+S2 | 157 | 197 | 0.454 | 2500 | 6.4 | S0 125, S6 63, S8a+S2 171 | * |
| S0 > S8a+S2 | 157 | 199 | 0.455 | 3199 | 8.2 | S0 125, S8a+S2 234 |  |

