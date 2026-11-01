## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 368 | 95% |
| right class selected | 286 | 74% |
| buggy method reached ranking | 240 | 62% |
| ranked in top 5 | 215 | 55% |
| ranked first | 124 | 32% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 19 |
| empty_unknown | 1 |
| class_missed | 82 |
| method_filtered_out | 46 |
| ranked_below_5 | 25 |
| rank_2_5 | 91 |
| top1 | 124 |

Crash reasons: no_failing_test_output: 16, other: 3

Tie-dependence: 58 of 124 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 7,359 |
| calls_truncated_by_length | 17 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 7 |
| no_valid_method | 11 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 2,253 |

## Per project

| Project | Attempted | crashed | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 0 | 3 | 3 | 1 | 9 | 10 |
| Closure | 131 | 4 | 0 | 44 | 15 | 14 | 29 | 25 |
| Lang | 61 | 0 | 0 | 5 | 9 | 0 | 14 | 33 |
| Math | 106 | 0 | 1 | 16 | 15 | 6 | 29 | 39 |
| Mockito | 38 | 15 | 0 | 7 | 3 | 2 | 4 | 7 |
| Time | 26 | 0 | 0 | 7 | 1 | 2 | 6 | 10 |
