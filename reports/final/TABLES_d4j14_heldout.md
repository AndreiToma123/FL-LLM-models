# Defects4J 1.4.0 - only the 288 bugs never used to design the judge (the 100-bug design sample of configs/selection_split.json left out): results over 1 run(s)

Judge = selector S8a+S2 replayed on each run's own candidate lists. Every bug counts; a bug without output is a miss. Median and range (min-max) over the runs that exist.

## Top-1

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 95 | 95 | 95-95 |
| SoapFL + judge | 119 | 119 | 119-119 |
| Class widening (always) | 102 | 102 | 102-102 |
| Class widening (always) + judge | 127 | 127 | 127-127 |
| Class widening (gated) | 99 | 99 | 99-99 |
| Class widening (gated) + judge | 122 | 122 | 122-122 |

## Top-3

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 143 | 143 | 143-143 |
| SoapFL + judge | 149 | 149 | 149-149 |
| Class widening (always) | 158 | 158 | 158-158 |
| Class widening (always) + judge | 167 | 167 | 167-167 |
| Class widening (gated) | 149 | 149 | 149-149 |
| Class widening (gated) + judge | 164 | 164 | 164-164 |

## Top-5

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 149 | 149 | 149-149 |
| SoapFL + judge | 153 | 153 | 153-153 |
| Class widening (always) | 171 | 171 | 171-171 |
| Class widening (always) + judge | 178 | 178 | 178-178 |
| Class widening (gated) | 161 | 161 | 161-161 |
| Class widening (gated) + judge | 167 | 167 | 167-167 |

## Bugs and cost

| Pipeline | bugs | without output (per run) | front-end calls / bug (bugs with output) | tokens / bug (bugs with output) | judge calls / bug (all bugs) |
|---|---:|---|---:|---:|---:|
| SoapFL | 288 | 19 | 11.7 | 29,704 | - |
| SoapFL + judge | 288 | 19 | 11.7 | 29,704 | 8.3 |
| Class widening (always) | 288 | 12 | 31.5 | 78,710 | - |
| Class widening (always) + judge | 288 | 12 | 31.5 | 78,710 | 17.5 |
| Class widening (gated) | 288 | 16 | 19.7 | 49,595 | - |
| Class widening (gated) + judge | 288 | 16 | 19.7 | 49,595 | 12.3 |

## Paired test against plain SoapFL (Top-1, exact McNemar on the median run of each pipeline)

One main comparison per research question (RQ1, RQ2, RQ3; this choice of main comparisons is Claude's proposal of 2026-11-09 and must be confirmed by the user before the official runs); the others are exploratory and their p-values are Holm-corrected. 'Runs with a gain' = in how many run pairs (run i vs run i of SoapFL) the pipeline gained more bugs than it lost.

| Pipeline vs SoapFL | role | median run used | gained / lost | p | p (Holm) | runs with a gain |
|---|---|---:|---:|---:|---:|---:|
| SoapFL + judge | RQ3 | 1 | +32 / -8 | 0.000182 | - | 1 of 1 |
| Class widening (always) | RQ1 | 1 | +15 / -8 | 0.21 | - | 1 of 1 |
| Class widening (always) + judge | exploratory | 1 | +46 / -14 | 4.22e-05 | 8.45e-05 | 1 of 1 |
| Class widening (gated) | RQ2 | 1 | +19 / -15 | 0.608 | - | 1 of 1 |
| Class widening (gated) + judge | exploratory | 1 | +42 / -15 | 0.00046 | 0.00046 | 1 of 1 |

## How many bugs change between runs (Top-1 hit or not)

| Pipeline | run pair | bugs that flip |
|---|---|---:|
