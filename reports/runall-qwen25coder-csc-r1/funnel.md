## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 359 | 93% |
| right class selected | 244 | 63% |
| buggy method reached ranking | 206 | 53% |
| ranked in top 5 | 199 | 51% |
| ranked first | 124 | 32% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 17 |
| no_valid_class | 7 |
| no_valid_method | 1 |
| empty_unknown | 4 |
| class_missed | 115 |
| method_filtered_out | 38 |
| ranked_below_5 | 7 |
| rank_2_5 | 75 |
| top1 | 124 |

Crash reasons: no_failing_test_output: 16, other: 1

Tie-dependence: 57 of 124 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 4,168 |
| calls_truncated_by_length | 6 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 8 |
| no_valid_method | 4 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 2,254 |

## Per project

| Project | Attempted | crashed | no_valid_class | no_valid_method | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 0 | 0 | 0 | 4 | 2 | 1 | 9 | 10 |
| Closure | 131 | 1 | 5 | 1 | 2 | 51 | 16 | 5 | 29 | 21 |
| Lang | 61 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 12 | 35 |
| Math | 106 | 1 | 1 | 0 | 1 | 27 | 12 | 1 | 20 | 43 |
| Mockito | 38 | 15 | 1 | 0 | 1 | 12 | 0 | 0 | 3 | 6 |
| Time | 26 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 2 | 9 |
