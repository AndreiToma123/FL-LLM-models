## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 100 | 100% |
| produced a ranking | 93 | 93% |
| right class selected | 62 | 62% |
| buggy method reached ranking | 51 | 51% |
| ranked in top 5 | 47 | 47% |
| ranked first | 28 | 28% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 6 |
| empty_unknown | 1 |
| class_missed | 31 |
| method_filtered_out | 11 |
| ranked_below_5 | 4 |
| rank_2_5 | 19 |
| top1 | 28 |

Crash reasons: no_failing_test_output: 6

Tie-dependence: 13 of 28 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 972 |
| calls_truncated_by_length | 4 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 1 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 11,885 |
| mean_prompt_tokens | 2,167 |

## Per project

| Project | Attempted | crashed | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Chart | 6 | 0 | 0 | 1 | 1 | 0 | 0 | 4 |
| Closure | 33 | 0 | 0 | 16 | 2 | 1 | 7 | 7 |
| Lang | 15 | 0 | 0 | 2 | 4 | 0 | 4 | 5 |
| Math | 27 | 0 | 1 | 6 | 4 | 3 | 5 | 8 |
| Mockito | 13 | 6 | 0 | 3 | 0 | 0 | 3 | 1 |
| Time | 6 | 0 | 0 | 3 | 0 | 0 | 0 | 3 |
