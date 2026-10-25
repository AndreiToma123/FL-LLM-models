## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 12 | 100% |
| produced a ranking | 12 | 100% |
| right class selected | 7 | 58% |
| buggy method reached ranking | 6 | 50% |
| ranked in top 5 | 6 | 50% |
| ranked first | 4 | 33% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| class_missed | 5 |
| method_filtered_out | 1 |
| rank_2_5 | 2 |
| top1 | 4 |

Tie-dependence: 3 of 4 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 117 |
| calls_truncated_by_length | 0 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 0 |
| no_valid_method | 0 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 6,337 |
| mean_prompt_tokens | 1,693 |

## Per project

| Project | Attempted | class_missed | method_filtered_out | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|
| Cli | 1 | 0 | 0 | 1 | 0 |
| Closure | 1 | 1 | 0 | 0 | 0 |
| Codec | 1 | 1 | 0 | 0 | 0 |
| Collections | 1 | 0 | 1 | 0 | 0 |
| Compress | 1 | 0 | 0 | 0 | 1 |
| Csv | 1 | 0 | 0 | 1 | 0 |
| Gson | 1 | 0 | 0 | 0 | 1 |
| JacksonCore | 1 | 1 | 0 | 0 | 0 |
| JacksonDatabind | 1 | 1 | 0 | 0 | 0 |
| JacksonXml | 1 | 0 | 0 | 0 | 1 |
| Jsoup | 1 | 1 | 0 | 0 | 0 |
| JxPath | 1 | 0 | 0 | 0 | 1 |
