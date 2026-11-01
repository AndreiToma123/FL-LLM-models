## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 3 | 100% |
| produced a ranking | 3 | 100% |
| right class selected | 2 | 67% |
| buggy method reached ranking | 1 | 33% |
| ranked in top 5 | 1 | 33% |
| ranked first | 1 | 33% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| class_missed | 1 |
| method_filtered_out | 1 |
| top1 | 1 |

Tie-dependence: 0 of 1 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 24 |
| calls_truncated_by_length | 0 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 0 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 4,870 |
| mean_prompt_tokens | 1,899 |

## Per project

| Project | Attempted | class_missed | method_filtered_out | top1 |
|---|---:|---:|---:|---:|
| Chart | 1 | 0 | 1 | 0 |
| Lang | 1 | 0 | 0 | 1 |
| Math | 1 | 1 | 0 | 0 |
