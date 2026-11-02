## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 439 | 99% |
| right class selected | 353 | 80% |
| buggy method reached ranking | 279 | 63% |
| ranked in top 5 | 219 | 49% |
| ranked first | 119 | 27% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 4 |
| no_valid_class | 1 |
| class_missed | 86 |
| method_filtered_out | 74 |
| ranked_below_5 | 60 |
| rank_2_5 | 100 |
| top1 | 119 |

Crash reasons: other: 3, context_overflow_server: 1

Tie-dependence: 84 of 119 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 44,643 |
| calls_truncated_by_length | 34 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 13 |
| no_valid_method | 98 |
| terminated_phases | 3 |
| context_overflow_guard | 3 |
| max_prompt_tokens | 15,276 |
| mean_prompt_tokens | 1,487 |

## Per project

| Project | Attempted | crashed | no_valid_class | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 0 | 0 | 7 | 6 | 4 | 11 | 11 |
| Closure | 43 | 2 | 0 | 5 | 8 | 10 | 12 | 6 |
| Codec | 18 | 0 | 0 | 2 | 1 | 2 | 3 | 10 |
| Collections | 4 | 0 | 0 | 0 | 3 | 0 | 1 | 0 |
| Compress | 47 | 0 | 0 | 0 | 5 | 2 | 15 | 25 |
| Csv | 16 | 0 | 0 | 2 | 5 | 1 | 3 | 5 |
| Gson | 18 | 0 | 1 | 4 | 2 | 1 | 5 | 5 |
| JacksonCore | 26 | 0 | 0 | 3 | 3 | 3 | 6 | 11 |
| JacksonDatabind | 112 | 0 | 0 | 46 | 18 | 13 | 22 | 13 |
| JacksonXml | 6 | 0 | 0 | 1 | 2 | 2 | 0 | 1 |
| Jsoup | 93 | 0 | 0 | 11 | 21 | 16 | 18 | 27 |
| JxPath | 22 | 2 | 0 | 5 | 0 | 6 | 4 | 5 |
