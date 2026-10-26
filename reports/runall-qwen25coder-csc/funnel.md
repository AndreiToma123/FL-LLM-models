## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 360 | 93% |
| right class selected | 246 | 63% |
| buggy method reached ranking | 207 | 53% |
| ranked in top 5 | 199 | 51% |
| ranked first | 130 | 34% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 17 |
| no_valid_class | 5 |
| no_valid_method | 3 |
| empty_unknown | 3 |
| class_missed | 114 |
| method_filtered_out | 39 |
| ranked_below_5 | 8 |
| rank_2_5 | 69 |
| top1 | 130 |

Crash reasons: no_failing_test_output: 16, other: 1

Tie-dependence: 61 of 130 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 4,132 |
| calls_truncated_by_length | 3 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 5 |
| no_valid_method | 4 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 2,226 |

## Per project

| Project | Attempted | crashed | no_valid_class | no_valid_method | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 0 | 1 | 0 | 3 | 4 | 1 | 7 | 10 |
| Closure | 131 | 1 | 3 | 1 | 2 | 56 | 15 | 3 | 22 | 28 |
| Lang | 61 | 1 | 0 | 0 | 0 | 5 | 10 | 1 | 9 | 35 |
| Math | 106 | 0 | 1 | 0 | 0 | 29 | 10 | 3 | 23 | 40 |
| Mockito | 38 | 15 | 1 | 1 | 1 | 10 | 0 | 0 | 3 | 7 |
| Time | 26 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 5 | 10 |
