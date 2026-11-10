## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 441 | 99% |
| right class selected | 308 | 69% |
| buggy method reached ranking | 252 | 57% |
| ranked in top 5 | 215 | 48% |
| ranked first | 117 | 26% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 2 |
| no_valid_class | 1 |
| class_missed | 133 |
| method_filtered_out | 56 |
| ranked_below_5 | 37 |
| rank_2_5 | 98 |
| top1 | 117 |

Crash reasons: other: 2

Tie-dependence: 67 of 117 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 14,665 |
| calls_truncated_by_length | 30 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 24 |
| no_valid_method | 33 |
| terminated_phases | 25 |
| context_overflow_guard | 25 |
| max_prompt_tokens | 15,276 |
| mean_prompt_tokens | 1,981 |

## Per project

| Project | Attempted | crashed | no_valid_class | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 0 | 0 | 7 | 5 | 0 | 14 | 13 |
| Closure | 43 | 1 | 0 | 7 | 7 | 6 | 17 | 5 |
| Codec | 18 | 0 | 0 | 2 | 3 | 1 | 5 | 7 |
| Collections | 4 | 0 | 0 | 0 | 3 | 0 | 1 | 0 |
| Compress | 47 | 0 | 0 | 4 | 5 | 6 | 8 | 24 |
| Csv | 16 | 0 | 0 | 4 | 5 | 0 | 4 | 3 |
| Gson | 18 | 0 | 1 | 4 | 3 | 1 | 4 | 5 |
| JacksonCore | 26 | 0 | 0 | 7 | 1 | 1 | 9 | 8 |
| JacksonDatabind | 112 | 0 | 0 | 66 | 6 | 10 | 13 | 17 |
| JacksonXml | 6 | 0 | 0 | 1 | 1 | 2 | 1 | 1 |
| Jsoup | 93 | 0 | 0 | 18 | 17 | 8 | 20 | 30 |
| JxPath | 22 | 1 | 0 | 13 | 0 | 2 | 2 | 4 |
