## Gated escalation on run100-qwen25coder (offline from cached selector runs; margin 0.5)

Cost = model calls a fresh run of the policy would make (calls of every selector a bug reached). Calls shared between selectors (S5+S2 repeats S5's pairs) are counted twice.

### dev (50 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 | 16 | 25 | 0.414 | 0 | 0.0 | S0 47 | * |
| S0 > S6 | 16 | 25 | 0.414 | 0 | 0.0 | S0 12, S6 35 |  |
| S0 > S6 > S8a+S2 | 21 | 27 | 0.479 | 451 | 9.0 | S0 12, S6 6, S8a+S2 29 | * |
| S0 > S8a+S2 | 21 | 27 | 0.479 | 498 | 10.0 | S0 12, S8a+S2 35 |  |

### test (50 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 13 | 19 | 0.326 | 0 | 0.0 | S0 16, S6 30 | * |
| S0 | 12 | 21 | 0.325 | 0 | 0.0 | S0 46 |  |
| S0 > S6 > S8a+S2 | 16 | 20 | 0.362 | 238 | 4.8 | S0 16, S6 12, S8a+S2 18 | * |
| S0 > S8a+S2 | 16 | 22 | 0.370 | 431 | 8.6 | S0 16, S8a+S2 30 |  |

### all (100 bugs)

| Policy | Top-1 | Top-3 | MRR | model calls | per bug | stopped at | Pareto |
|---|---:|---:|---:|---:|---:|---|:-:|
| S0 > S6 | 29 | 44 | 0.370 | 0 | 0.0 | S0 28, S6 65 | * |
| S0 | 28 | 46 | 0.370 | 0 | 0.0 | S0 93 |  |
| S0 > S6 > S8a+S2 | 37 | 47 | 0.421 | 689 | 6.9 | S0 28, S6 18, S8a+S2 47 | * |
| S0 > S8a+S2 | 37 | 49 | 0.424 | 929 | 9.3 | S0 28, S8a+S2 65 |  |

