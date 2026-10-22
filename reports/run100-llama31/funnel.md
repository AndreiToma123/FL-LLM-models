## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 100 | 100% |
| produced a ranking | 89 | 89% |
| right class selected | 54 | 54% |
| buggy method reached ranking | 48 | 48% |
| ranked in top 5 | 44 | 44% |
| ranked first | 14 | 14% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 7 |
| no_valid_class | 2 |
| no_valid_method | 1 |
| empty_unknown | 1 |
| class_missed | 35 |
| method_filtered_out | 6 |
| ranked_below_5 | 4 |
| rank_2_5 | 30 |
| top1 | 14 |

Crash reasons: no_failing_test_output: 6, other: 1

Tie-dependence: 8 of 14 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 1,038 |
| calls_truncated_by_length | 2 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 4 |
| no_valid_method | 1 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 11,815 |
| mean_prompt_tokens | 2,060 |

## Per project

| Project | Attempted | crashed | no_valid_class | no_valid_method | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chart | 6 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 4 | 1 |
| Closure | 33 | 0 | 0 | 0 | 1 | 19 | 1 | 2 | 8 | 2 |
| Lang | 15 | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 8 | 3 |
| Math | 27 | 0 | 1 | 1 | 0 | 7 | 2 | 2 | 8 | 6 |
| Mockito | 13 | 6 | 1 | 0 | 0 | 2 | 2 | 0 | 1 | 1 |
| Time | 6 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 1 | 1 |
