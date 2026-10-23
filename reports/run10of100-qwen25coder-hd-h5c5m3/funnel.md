## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 10 | 100% |
| produced a ranking | 9 | 90% |
| right class selected | 8 | 80% |
| buggy method reached ranking | 7 | 70% |
| ranked in top 5 | 3 | 30% |
| ranked first | 0 | 0% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 1 |
| class_missed | 1 |
| method_filtered_out | 1 |
| ranked_below_5 | 4 |
| rank_2_5 | 3 |

Crash reasons: no_failing_test_output: 1

## Events

| Event | Count |
|---|---:|
| llm_calls | 997 |
| calls_truncated_by_length | 4 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 0 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 8,601 |
| mean_prompt_tokens | 2,052 |

## Per project

| Project | Attempted | crashed | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 |
|---|---:|---:|---:|---:|---:|---:|
| Chart | 1 | 0 | 0 | 0 | 1 | 0 |
| Closure | 3 | 0 | 1 | 0 | 0 | 2 |
| Lang | 1 | 0 | 0 | 0 | 1 | 0 |
| Math | 3 | 0 | 0 | 1 | 2 | 0 |
| Mockito | 1 | 1 | 0 | 0 | 0 | 0 |
| Time | 1 | 0 | 0 | 0 | 0 | 1 |
