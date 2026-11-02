## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 345 | 89% |
| right class selected | 294 | 76% |
| buggy method reached ranking | 238 | 61% |
| ranked in top 5 | 200 | 52% |
| ranked first | 118 | 30% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 43 |
| class_missed | 51 |
| method_filtered_out | 56 |
| ranked_below_5 | 38 |
| rank_2_5 | 82 |
| top1 | 118 |

Crash reasons: other: 26, no_failing_test_output: 16, timeout: 1

Tie-dependence: 83 of 118 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 32,184 |
| calls_truncated_by_length | 67 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 72 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 1,857 |

## Per project

| Project | Attempted | crashed | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 4 | 4 | 2 | 4 | 12 |
| Closure | 131 | 3 | 36 | 29 | 16 | 28 | 19 |
| Lang | 61 | 0 | 3 | 4 | 3 | 15 | 36 |
| Math | 106 | 2 | 3 | 16 | 13 | 29 | 43 |
| Mockito | 38 | 38 | 0 | 0 | 0 | 0 | 0 |
| Time | 26 | 0 | 5 | 3 | 4 | 6 | 8 |
