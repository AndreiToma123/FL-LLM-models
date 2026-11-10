## Gated escalation on runall-qwen25coder-ca3g-csc (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (388 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 132 | 208 | 0.439 | 0 | 0.0 | S0 115, S6 253 | * |
| S0 | 124 | 200 | 0.421 | 0 | 0.0 | S0 368 |  |
| S0 > S6 > S8a+S2 | 152 | 214 | 0.473 | 3611 | 9.3 | S0 115, S6 72, S8a+S2 181 | * |
| S0 > S8a+S2 | 158 | 214 | 0.482 | 5134 | 13.2 | S0 115, S8a+S2 253 | * |

