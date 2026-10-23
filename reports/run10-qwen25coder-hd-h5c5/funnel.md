## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 10 | 100% |
| produced a ranking | 8 | 80% |
| right class selected | 6 | 60% |
| buggy method reached ranking | 6 | 60% |
| ranked in top 5 | 5 | 50% |
| ranked first | 1 | 10% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 2 |
| class_missed | 2 |
| ranked_below_5 | 1 |
| rank_2_5 | 4 |
| top1 | 1 |

Crash reasons: model_not_found: 1, no_failing_test_output: 1

Tie-dependence: 0 of 1 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 2,206 |
| calls_truncated_by_length | 11 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 1 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 8,601 |
| mean_prompt_tokens | 2,165 |

## Per project

| Project | Attempted | crashed | class_missed | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|
| Chart | 1 | 1 | 0 | 0 | 0 | 0 |
| Closure | 3 | 0 | 1 | 0 | 2 | 0 |
| Lang | 1 | 0 | 0 | 0 | 1 | 0 |
| Math | 2 | 0 | 0 | 0 | 1 | 1 |
| Mockito | 2 | 1 | 1 | 0 | 0 | 0 |
| Time | 1 | 0 | 0 | 1 | 0 | 0 |
