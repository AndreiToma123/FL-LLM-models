# Defects4J 1.4.0 - only the 288 bugs never used to design the judge (the 100-bug design sample of configs/selection_split.json left out): results over 1 run(s)

Judge = selector S8a+S2 replayed on each run's own candidate lists. Every bug counts; a bug without output is a miss. Median and range (min-max) over the runs that exist.

## Top-1

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 102 | 102 | 102-102 |
| SoapFL + judge | 116 | 116 | 116-116 |
| Class widening (always) | 107 | 107 | 107-107 |
| Class widening (always) + judge | 130 | 130 | 130-130 |
| Class widening (gated) | 94 | 94 | 94-94 |
| Class widening (gated) + judge | 120 | 120 | 120-120 |

## Top-3

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 144 | 144 | 144-144 |
| SoapFL + judge | 148 | 148 | 148-148 |
| Class widening (always) | 158 | 158 | 158-158 |
| Class widening (always) + judge | 169 | 169 | 169-169 |
| Class widening (gated) | 150 | 150 | 150-150 |
| Class widening (gated) + judge | 161 | 161 | 161-161 |

## Top-5

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 152 | 152 | 152-152 |
| SoapFL + judge | 153 | 153 | 153-153 |
| Class widening (always) | 176 | 176 | 176-176 |
| Class widening (always) + judge | 181 | 181 | 181-181 |
| Class widening (gated) | 160 | 160 | 160-160 |
| Class widening (gated) + judge | 167 | 167 | 167-167 |

## Bugs and cost

| Pipeline | bugs | without output (per run) | front-end calls / bug (bugs with output) | tokens / bug (bugs with output) | judge calls / bug (all bugs) |
|---|---:|---|---:|---:|---:|
| SoapFL | 288 | 20 | 11.6 | 29,629 | - |
| SoapFL + judge | 288 | 20 | 11.6 | 29,629 | 7.2 |
| Class widening (always) | 288 | 14 | 31.2 | 78,592 | - |
| Class widening (always) + judge | 288 | 14 | 31.2 | 78,592 | 17.9 |
| Class widening (gated) | 288 | 13 | 20.1 | 50,524 | - |
| Class widening (gated) + judge | 288 | 13 | 20.1 | 50,524 | 13.7 |

## Paired test against plain SoapFL (Top-1, exact McNemar on the median run of each pipeline)

One main comparison per research question (RQ1, RQ2, RQ3; this choice of main comparisons is Claude's proposal of 2026-11-09 and must be confirmed by the user before the official runs); the others are exploratory and their p-values are Holm-corrected. 'Runs with a gain' = in how many run pairs (run i vs run i of SoapFL) the pipeline gained more bugs than it lost.

| Pipeline vs SoapFL | role | median run used | gained / lost | p | p (Holm) | runs with a gain |
|---|---|---:|---:|---:|---:|---:|
| SoapFL + judge | RQ3 | 1 | +22 / -8 | 0.0161 | - | 1 of 1 |
| Class widening (always) | RQ1 | 1 | +20 / -15 | 0.5 | - | 1 of 1 |
| Class widening (always) + judge | exploratory | 1 | +42 / -14 | 0.000234 | 0.000469 | 1 of 1 |
| Class widening (gated) | RQ2 | 1 | +10 / -18 | 0.185 | - | 0 of 1 |
| Class widening (gated) + judge | exploratory | 1 | +33 / -15 | 0.0133 | 0.0133 | 1 of 1 |

## How many bugs change between runs (Top-1 hit or not)

| Pipeline | run pair | bugs that flip |
|---|---|---:|
