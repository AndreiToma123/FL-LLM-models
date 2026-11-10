# Bug bookkeeping (A5)

**395 vs 388 (dataset 1):** SoapFL's own `run_all.py` skips 7 bug ids, so the batch has 388 bugs while the paper's Table I lists 395: Time-21, Lang-2, Lang-18, Lang-25, Lang-48, Closure-63, Closure-93 (`fl_tools/bugs.py`, `deprecate`). Defects4J marks these ids deprecated. They are not run in any of our pipelines.

## runall-qwen25coder-csc-r1

388 bugs, 359 with output, 29 without:

| status / reason | bugs | which |
|---|---:|---|
| failed / no_failing_test_output | 16 | Closure-115, Mockito-1, Mockito-10, Mockito-11, Mockito-18, Mockito-19, Mockito-2, Mockito-20, Mockito-21, Mockito-3, Mockito-4, Mockito-5, Mockito-6, Mockito-7, Mockito-8, Mockito-9 |
| no_result / - | 12 | Closure-13, Closure-31, Closure-36, Closure-42, Closure-57, Closure-84, Closure-91, Closure-97, Math-29, Math-78, Mockito-17, Mockito-23 |
| failed / other | 1 | Math-54 |

Mockito without output: 17 (failed / no_failing_test_output: 15, no_result / -: 2)

## runall-qwen25coder-ca3-csc-r1

388 bugs, 369 with output, 19 without:

| status / reason | bugs | which |
|---|---:|---|
| failed / no_failing_test_output | 16 | Closure-115, Mockito-1, Mockito-10, Mockito-11, Mockito-18, Mockito-19, Mockito-2, Mockito-20, Mockito-21, Mockito-3, Mockito-4, Mockito-5, Mockito-6, Mockito-7, Mockito-8, Mockito-9 |
| failed / other | 3 | Closure-118, Closure-36, Closure-40 |

Mockito without output: 15 (failed / no_failing_test_output: 15)

## runall-qwen25coder-ca3g-csc-r1

388 bugs, 365 with output, 23 without:

| status / reason | bugs | which |
|---|---:|---|
| failed / no_failing_test_output | 16 | Closure-115, Mockito-1, Mockito-10, Mockito-11, Mockito-18, Mockito-19, Mockito-2, Mockito-20, Mockito-21, Mockito-3, Mockito-4, Mockito-5, Mockito-6, Mockito-7, Mockito-8, Mockito-9 |
| failed / other | 5 | Closure-129, Closure-13, Closure-36, Closure-40, Math-54 |
| no_result / - | 2 | Closure-124, Mockito-38 |

Mockito without output: 16 (failed / no_failing_test_output: 15, no_result / -: 1)

