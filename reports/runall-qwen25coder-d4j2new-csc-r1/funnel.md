## Funnel

| Stage | Bugs | % of attempted |
|---|---:|---:|
| attempted | 444 | 100% |
| produced a ranking | 423 | 95% |
| right class selected | 238 | 54% |
| buggy method reached ranking | 185 | 42% |
| ranked in top 5 | 177 | 40% |
| ranked first | 104 | 23% |

## Where bugs were lost

| Terminal stage | Bugs |
|---|---:|
| crashed | 1 |
| no_valid_class | 17 |
| no_valid_method | 1 |
| empty_unknown | 2 |
| class_missed | 185 |
| method_filtered_out | 53 |
| ranked_below_5 | 8 |
| rank_2_5 | 73 |
| top1 | 104 |

Crash reasons: other: 1

Tie-dependence: 40 of 104 Top-1 hits share their score with at least one other reviewed method, so they depend on review order.

## Events

| Event | Count |
|---|---:|
| llm_calls | 4,928 |
| calls_truncated_by_length | 3 |
| calls_with_think_block | 0 |
| score_unparsed | 0 |
| no_valid_class | 22 |
| no_valid_method | 4 |
| terminated_phases | 0 |
| context_overflow_guard | 0 |
| max_prompt_tokens | 15,209 |
| mean_prompt_tokens | 1,842 |

## Per project

| Project | Attempted | crashed | no_valid_class | no_valid_method | empty_unknown | class_missed | method_filtered_out | ranked_below_5 | rank_2_5 | top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Cli | 39 | 0 | 0 | 0 | 0 | 14 | 5 | 0 | 8 | 12 |
| Closure | 43 | 0 | 0 | 0 | 0 | 15 | 10 | 1 | 11 | 6 |
| Codec | 18 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 5 | 7 |
| Collections | 4 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 |
| Compress | 47 | 0 | 1 | 0 | 0 | 12 | 4 | 1 | 8 | 21 |
| Csv | 16 | 0 | 0 | 0 | 0 | 7 | 3 | 0 | 4 | 2 |
| Gson | 18 | 0 | 1 | 0 | 0 | 6 | 1 | 0 | 4 | 6 |
| JacksonCore | 26 | 0 | 0 | 0 | 0 | 7 | 1 | 0 | 11 | 7 |
| JacksonDatabind | 112 | 0 | 12 | 1 | 1 | 68 | 9 | 1 | 6 | 14 |
| JacksonXml | 6 | 0 | 0 | 0 | 0 | 4 | 1 | 0 | 0 | 1 |
| Jsoup | 93 | 0 | 2 | 0 | 0 | 35 | 12 | 3 | 15 | 26 |
| JxPath | 22 | 1 | 1 | 0 | 1 | 13 | 1 | 2 | 1 | 2 |
