## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 388 | 100% |
| produced a ranking | 365 | 94% |
| right class selected | 286 | 74% |
| buggy method reached ranking | 236 | 61% |
| ranked in top 5 | 217 | 56% |
| ranked first | 132 | 34% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 21 |
| no_valid_method | 2 |
| class_missed | 79 |
| method_filtered_out | 50 |
| ranked_below_5 | 19 |
| rank_2_5 | 85 |
| top1 | 132 |

Crash reasons: no_failing_test_output: 16, other: 5

Tie-dependence: 67 of 132 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 7,219 |
| calls_truncated_by_length | 15 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 9 |
| no_valid_method | 14 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 14,516 |
| mean_prompt_tokens | 2,261 |

## Per project

| Project | Attempted | crashed | no_valid_method | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Chart | 26 | 0 | 0 | 3 | 4 | 0 | 9 | 10 |
| Closure | 131 | 5 | 1 | 39 | 18 | 14 | 27 | 27 |
| Lang | 61 | 0 | 0 | 4 | 8 | 2 | 12 | 35 |
| Math | 106 | 1 | 0 | 19 | 13 | 1 | 26 | 46 |
| Mockito | 38 | 15 | 1 | 7 | 3 | 1 | 4 | 7 |
| Time | 26 | 0 | 0 | 7 | 4 | 1 | 7 | 7 |
