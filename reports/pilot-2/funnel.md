## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 20 | 100% |
| produced a ranking | 19 | 95% |
| right class selected | 14 | 70% |
| buggy method reached ranking | 11 | 55% |
| ranked in top 5 | 10 | 50% |
| ranked first | 5 | 25% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| empty_unknown | 1 |
| class_missed | 5 |
| method_filtered_out | 3 |
| ranked_below_5 | 1 |
| rank_2_5 | 5 |
| top1 | 5 |

Tie-dependence: 4 of 5 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 191 |
| calls_truncated_by_length | 4 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 0 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 7,061 |
| mean_prompt_tokens | 2,023 |

## Per project

| Project | Attempted | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Chart | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| Closure | 6 | 0 | 1 | 0 | 1 | 3 | 1 |
| Lang | 3 | 0 | 0 | 1 | 0 | 0 | 2 |
| Math | 5 | 0 | 1 | 2 | 0 | 0 | 2 |
| Mockito | 4 | 1 | 2 | 0 | 0 | 1 | 0 |
| Time | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
