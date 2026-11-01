## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 367 | 95% |
| right class selected | 311 | 80% |
| buggy method reached ranking | 259 | 67% |
| ranked in top 5 | 234 | 60% |
| ranked first | 134 | 35% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 21 |
| class_missed | 56 |
| method_filtered_out | 52 |
| ranked_below_5 | 25 |
| rank_2_5 | 100 |
| top1 | 134 |

Crash reasons: no_failing_test_output: 16, other: 5

Tie-dependence: 83 of 134 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 11,554 |
| calls_truncated_by_length | 26 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 6 |
| no_valid_method | 31 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 2,268 |

## Per project

| Project | Attempted | crashed | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 2 | 5 | 1 | 8 | 10 |
| Closure | 131 | 5 | 32 | 20 | 13 | 31 | 30 |
| Lang | 61 | 0 | 3 | 9 | 1 | 16 | 32 |
| Math | 106 | 1 | 9 | 13 | 6 | 33 | 44 |
| Mockito | 38 | 15 | 6 | 3 | 2 | 4 | 8 |
| Time | 26 | 0 | 4 | 2 | 2 | 8 | 10 |
