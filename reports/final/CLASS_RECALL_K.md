# Class recall for k = 1..5 (A4)

Bugs with output, a failure-context file and a known answer. 'Free ranking top-k' = the class ranking used by class widening (stack position, name overlap, coverage; fixed key). 'SoapFL + top-k' = SoapFL's own class plus the free ranking's top k (what class widening 'always' tries; the real pipeline can only add classes SoapFL offered to its model, so it can be a little lower). k = 3 was fixed after an offline study on dataset 1 AND dataset 2 class results (roadmap 3l), so neither dataset is a clean test of k.

## runall-qwen25coder-csc (352 bugs)

SoapFL's own class: 240 (68%)

| k | free ranking top-k | SoapFL + free top-k |
|---:|---:|---:|
| 1 | 230 (65%) | 258 (73%) |
| 2 | 282 (80%) | 294 (84%) |
| 3 | 305 (87%) | 310 (88%) |
| 4 | 317 (90%) | 320 (91%) |
| 5 | 324 (92%) | 327 (93%) |

## runall-qwen25coder-d4j2new-csc (407 bugs)

SoapFL's own class: 220 (54%)

| k | free ranking top-k | SoapFL + free top-k |
|---:|---:|---:|
| 1 | 206 (51%) | 254 (62%) |
| 2 | 255 (63%) | 281 (69%) |
| 3 | 285 (70%) | 303 (74%) |
| 4 | 306 (75%) | 321 (79%) |
| 5 | 316 (78%) | 330 (81%) |

