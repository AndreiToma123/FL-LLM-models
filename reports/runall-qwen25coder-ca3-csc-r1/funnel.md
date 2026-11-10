## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 369 | 95% |
| right class selected | 314 | 81% |
| buggy method reached ranking | 257 | 66% |
| ranked in top 5 | 229 | 59% |
| ranked first | 133 | 34% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 19 |
| class_missed | 55 |
| method_filtered_out | 57 |
| ranked_below_5 | 28 |
| rank_2_5 | 96 |
| top1 | 133 |

Crash reasons: no_failing_test_output: 16, other: 3

Tie-dependence: 85 of 133 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 11,608 |
| calls_truncated_by_length | 34 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 8 |
| no_valid_method | 27 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 2,273 |

## Per project

| Project | Attempted | crashed | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 2 | 5 | 1 | 5 | 13 |
| Closure | 131 | 4 | 33 | 22 | 17 | 35 | 20 |
| Lang | 61 | 0 | 3 | 9 | 0 | 14 | 35 |
| Math | 106 | 0 | 7 | 17 | 7 | 28 | 47 |
| Mockito | 38 | 15 | 6 | 3 | 0 | 7 | 7 |
| Time | 26 | 0 | 4 | 1 | 3 | 7 | 11 |
