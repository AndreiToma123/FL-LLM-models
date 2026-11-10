# Per-bug results (A6)

Every bug of the dataset counts; no output = not found. MRR = average of 1/rank over all bugs (not found = 0). Mean rank = over the bugs whose buggy method is in the list.

| Run | bugs | with output | Top-1 | Top-3 | Top-5 | found | MRR | mean rank (found) | right class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| runall-qwen25coder-csc-r1 | 388 | 359 | 124 | 190 | 199 | 206 | 0.402 | 1.84 | 244 |
| runall-qwen25coder-csc-r1 + S8a+S2 | 388 | 359 | 157 | 199 | 204 | 206 | 0.455 | 1.51 | 244 |
