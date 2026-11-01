## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 440 | 99% |
| right class selected | 306 | 69% |
| buggy method reached ranking | 253 | 57% |
| ranked in top 5 | 213 | 48% |
| ranked first | 107 | 24% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 3 |
| no_valid_class | 1 |
| class_missed | 134 |
| method_filtered_out | 53 |
| ranked_below_5 | 40 |
| rank_2_5 | 106 |
| top1 | 107 |

Crash reasons: other: 3

Tie-dependence: 60 of 107 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 14,610 |
| calls_truncated_by_length | 31 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 21 |
| no_valid_method | 28 |
| terminated_phases | 25 |
| context_overflow_guard | 25 |
| max_prompt_tokens | 15,276 |
| mean_prompt_tokens | 1,967 |

## Per project

| Project | Attempted | crashed | no_valid_class | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 0 | 0 | 6 | 5 | 2 | 16 | 10 |
| Closure | 43 | 1 | 0 | 8 | 7 | 5 | 16 | 6 |
| Codec | 18 | 0 | 0 | 2 | 2 | 0 | 8 | 6 |
| Collections | 4 | 0 | 0 | 0 | 3 | 1 | 0 | 0 |
| Compress | 47 | 0 | 0 | 4 | 4 | 5 | 11 | 23 |
| Csv | 16 | 0 | 0 | 4 | 5 | 0 | 4 | 3 |
| Gson | 18 | 0 | 1 | 4 | 2 | 2 | 4 | 5 |
| JacksonCore | 26 | 0 | 0 | 7 | 1 | 1 | 9 | 8 |
| JacksonDatabind | 112 | 1 | 0 | 68 | 5 | 11 | 12 | 15 |
| JacksonXml | 6 | 0 | 0 | 1 | 1 | 2 | 1 | 1 |
| Jsoup | 93 | 0 | 0 | 19 | 17 | 10 | 22 | 25 |
| JxPath | 22 | 1 | 0 | 11 | 1 | 1 | 3 | 5 |
