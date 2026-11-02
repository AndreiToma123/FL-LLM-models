## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 369 | 95% |
| right class selected | 310 | 80% |
| buggy method reached ranking | 253 | 65% |
| ranked in top 5 | 213 | 55% |
| ranked first | 127 | 33% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 19 |
| class_missed | 59 |
| method_filtered_out | 57 |
| ranked_below_5 | 40 |
| rank_2_5 | 86 |
| top1 | 127 |

Crash reasons: no_failing_test_output: 16, other: 3

Tie-dependence: 91 of 127 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 34,659 |
| calls_truncated_by_length | 68 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 1 |
| no_valid_method | 73 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 1,881 |

## Per project

| Project | Attempted | crashed | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 4 | 4 | 2 | 4 | 12 |
| Closure | 131 | 3 | 36 | 29 | 16 | 28 | 19 |
| Lang | 61 | 0 | 3 | 4 | 3 | 15 | 36 |
| Math | 106 | 1 | 3 | 16 | 13 | 30 | 43 |
| Mockito | 38 | 15 | 8 | 1 | 2 | 3 | 9 |
| Time | 26 | 0 | 5 | 3 | 4 | 6 | 8 |
