# Cost per bug (A2)

**One model call = one question sent to the model.** A pair of methods judged in both orders = 2 calls; a log-probability score question = 1 call. Front-end calls are averaged over the bugs with output (`per_bug.csv`, column `llm_calls`); judge calls over all bugs of the dataset (bugs the judge does not need to look at count as 0), and include answers taken from the cache, because a fresh run would ask them.

| Run | front-end calls / bug | tokens / bug | judge calls / bug (S8a+S2) | total calls / bug |
|---|---:|---:|---:|---:|
| runall-qwen25coder-csc | 11.4 | 28,343 | 7.3 | 18.7 |
| runall-qwen25coder-ca3-csc | 31.4 | 77,076 | 17.9 | 49.3 |
| runall-qwen25coder-ca3g-csc | 19.9 | 49,158 | 13.2 | 33.1 |
