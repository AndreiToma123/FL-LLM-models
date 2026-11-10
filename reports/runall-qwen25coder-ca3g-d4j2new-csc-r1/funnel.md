## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 441 | 99% |
| right class selected | 288 | 65% |
| buggy method reached ranking | 234 | 53% |
| ranked in top 5 | 202 | 45% |
| ranked first | 111 | 25% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 2 |
| no_valid_class | 1 |
| class_missed | 153 |
| method_filtered_out | 54 |
| ranked_below_5 | 32 |
| rank_2_5 | 91 |
| top1 | 111 |

Crash reasons: other: 2

Tie-dependence: 54 of 111 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 11,770 |
| calls_truncated_by_length | 32 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 21 |
| no_valid_method | 18 |
| terminated_phases | 24 |
| context_overflow_guard | 24 |
| max_prompt_tokens | 15,276 |
| mean_prompt_tokens | 1,938 |

## Per project

| Project | Attempted | crashed | no_valid_class | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 0 | 0 | 9 | 7 | 2 | 8 | 13 |
| Closure | 43 | 1 | 0 | 11 | 5 | 8 | 12 | 6 |
| Codec | 18 | 0 | 0 | 2 | 3 | 1 | 6 | 6 |
| Collections | 4 | 0 | 0 | 1 | 3 | 0 | 0 | 0 |
| Compress | 47 | 0 | 0 | 8 | 3 | 4 | 13 | 19 |
| Csv | 16 | 0 | 0 | 6 | 2 | 0 | 4 | 4 |
| Gson | 18 | 0 | 1 | 6 | 2 | 0 | 3 | 6 |
| JacksonCore | 26 | 0 | 0 | 6 | 2 | 1 | 8 | 9 |
| JacksonDatabind | 112 | 0 | 0 | 69 | 6 | 7 | 16 | 14 |
| JacksonXml | 6 | 0 | 0 | 3 | 1 | 0 | 1 | 1 |
| Jsoup | 93 | 0 | 0 | 21 | 20 | 7 | 18 | 27 |
| JxPath | 22 | 1 | 0 | 11 | 0 | 2 | 2 | 6 |
