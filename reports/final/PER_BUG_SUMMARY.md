# Per-bug results (A6)

Every bug of the dataset counts; no output = not found. MRR = average of 1/rank over all bugs (not found = 0). Mean rank = over the bugs whose buggy method is in the list.

| Run | bugs | with output | Top-1 | Top-3 | Top-5 | found | MRR | mean rank (found) | right class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| runall-qwen25coder-csc | 388 | 360 | 130 | 191 | 199 | 207 | 0.412 | 1.8 | 240 |
| runall-qwen25coder-csc + S8a+S2 | 388 | 360 | 152 | 195 | 201 | 207 | 0.446 | 1.61 | 240 |
| runall-qwen25coder-d4j2new-csc | 444 | 419 | 110 | 167 | 178 | 189 | 0.316 | 2 | 220 |
| runall-qwen25coder-d4j2new-csc + S8a+S2 | 444 | 419 | 137 | 170 | 180 | 189 | 0.351 | 1.76 | 220 |
