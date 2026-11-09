# Cost per bug (A2)

**One model call = one question sent to the model.** A pair of methods judged in both orders = 2 calls; a log-probability score question = 1 call. Front-end calls are averaged over the bugs with output (`per_bug.csv`, column `llm_calls`); judge calls over all bugs of the dataset (bugs the judge does not need to look at count as 0), and include answers taken from the cache, because a fresh run would ask them.

| Run | front-end calls / bug | tokens / bug | judge calls / bug (S8a+S2) | total calls / bug |
|---|---:|---:|---:|---:|
| runall-qwen25coder-d4j2new-csc | 11.3 | 23,428 | 7.5 | 18.8 |
| runall-qwen25coder-ca3-d4j2new-csc | 33.2 | 71,089 | 21.5 | 54.7 |
| runall-qwen25coder-ca3g-d4j2new-csc | 26.6 | 56,275 | 16.4 | 43.0 |
