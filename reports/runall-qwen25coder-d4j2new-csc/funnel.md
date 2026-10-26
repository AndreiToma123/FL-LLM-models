## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 419 | 94% |
| right class selected | 235 | 53% |
| buggy method reached ranking | 189 | 43% |
| ranked in top 5 | 178 | 40% |
| ranked first | 110 | 25% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 2 |
| no_valid_class | 20 |
| no_valid_method | 2 |
| empty_unknown | 1 |
| class_missed | 184 |
| method_filtered_out | 46 |
| ranked_below_5 | 11 |
| rank_2_5 | 68 |
| top1 | 110 |

Crash reasons: other: 2

Tie-dependence: 49 of 110 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 4,826 |
| calls_truncated_by_length | 2 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 22 |
| no_valid_method | 4 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 13,977 |
| mean_prompt_tokens | 1,824 |

## Per project

| Project | Attempted | crashed | no_valid_class | no_valid_method | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 1 | 0 | 0 | 0 | 13 | 6 | 0 | 5 | 14 |
| Closure | 43 | 1 | 0 | 0 | 0 | 15 | 7 | 3 | 9 | 8 |
| Codec | 18 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 7 | 5 |
| Collections | 4 | 0 | 1 | 0 | 0 | 1 | 2 | 0 | 0 | 0 |
| Compress | 47 | 0 | 1 | 0 | 0 | 13 | 2 | 2 | 9 | 20 |
| Csv | 16 | 0 | 0 | 0 | 0 | 6 | 2 | 0 | 4 | 4 |
| Gson | 18 | 0 | 3 | 0 | 0 | 6 | 1 | 0 | 2 | 6 |
| JacksonCore | 26 | 0 | 0 | 1 | 0 | 7 | 0 | 1 | 8 | 9 |
| JacksonDatabind | 112 | 0 | 11 | 1 | 1 | 72 | 7 | 0 | 6 | 14 |
| JacksonXml | 6 | 0 | 0 | 0 | 0 | 4 | 1 | 0 | 0 | 1 |
| Jsoup | 93 | 0 | 1 | 0 | 0 | 34 | 13 | 4 | 16 | 25 |
| JxPath | 22 | 0 | 3 | 0 | 0 | 10 | 2 | 1 | 2 | 4 |
