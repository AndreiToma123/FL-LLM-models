## Gated escalation on runall-qwen25coder-ca3-d4j2new-csc-r1 (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### all (444 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 128 | 187 | 0.371 | 0 | 0.0 | S0 101, S6 340 | * |
| S0 | 117 | 189 | 0.356 | 0 | 0.0 | S0 441 |  |
| S0 > S6 > S8a+S2 | 147 | 202 | 0.404 | 6265 | 14.1 | S0 101, S6 129, S8a+S2 211 | * |
| S0 > S8a+S2 | 145 | 207 | 0.403 | 8979 | 20.2 | S0 101, S8a+S2 340 |  |

