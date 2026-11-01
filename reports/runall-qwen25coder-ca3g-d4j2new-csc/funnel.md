## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 441 | 99% |
| right class selected | 290 | 65% |
| buggy method reached ranking | 236 | 53% |
| ranked in top 5 | 206 | 46% |
| ranked first | 118 | 27% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 2 |
| no_valid_class | 1 |
| class_missed | 151 |
| method_filtered_out | 54 |
| ranked_below_5 | 30 |
| rank_2_5 | 88 |
| top1 | 118 |

Crash reasons: other: 2

Tie-dependence: 54 of 118 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 11,771 |
| calls_truncated_by_length | 28 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 27 |
| no_valid_method | 14 |
| terminated_phases | 24 |
| context_overflow_guard | 24 |
| max_prompt_tokens | 15,276 |
| mean_prompt_tokens | 1,930 |

## Per project

| Project | Attempted | crashed | no_valid_class | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 0 | 0 | 7 | 6 | 3 | 7 | 16 |
| Closure | 43 | 1 | 0 | 9 | 7 | 5 | 14 | 7 |
| Codec | 18 | 0 | 0 | 2 | 1 | 1 | 6 | 8 |
| Collections | 4 | 0 | 0 | 1 | 3 | 0 | 0 | 0 |
| Compress | 47 | 0 | 0 | 9 | 2 | 4 | 11 | 21 |
| Csv | 16 | 0 | 0 | 6 | 4 | 0 | 2 | 4 |
| Gson | 18 | 0 | 1 | 6 | 2 | 0 | 3 | 6 |
| JacksonCore | 26 | 0 | 0 | 8 | 1 | 1 | 9 | 7 |
| JacksonDatabind | 112 | 0 | 0 | 69 | 7 | 6 | 13 | 17 |
| JacksonXml | 6 | 0 | 0 | 3 | 1 | 0 | 1 | 1 |
| Jsoup | 93 | 0 | 0 | 20 | 20 | 8 | 19 | 26 |
| JxPath | 22 | 1 | 0 | 11 | 0 | 2 | 3 | 5 |
