# Defects4J 1.4.0: results over 1 run(s)

Judge = selector S8a+S2 replayed on each run's own candidate lists. Every bug counts; a bug without output is a miss. Median and range (min-max) over the runs that exist.

## Top-1

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 124 | 124 | 124-124 |
| SoapFL + judge | 157 | 157 | 157-157 |
| Class widening (always) | 133 | 133 | 133-133 |
| Class widening (always) + judge | 170 | 170 | 170-170 |
| Class widening (gated) | 132 | 132 | 132-132 |
| Class widening (gated) + judge | 160 | 160 | 160-160 |

## Top-3

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 190 | 190 | 190-190 |
| SoapFL + judge | 199 | 199 | 199-199 |
| Class widening (always) | 210 | 210 | 210-210 |
| Class widening (always) + judge | 227 | 227 | 227-227 |
| Class widening (gated) | 203 | 203 | 203-203 |
| Class widening (gated) + judge | 217 | 217 | 217-217 |

## Top-5

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 199 | 199 | 199-199 |
| SoapFL + judge | 204 | 204 | 204-204 |
| Class widening (always) | 229 | 229 | 229-229 |
| Class widening (always) + judge | 239 | 239 | 239-239 |
| Class widening (gated) | 217 | 217 | 217-217 |
| Class widening (gated) + judge | 223 | 223 | 223-223 |

## Bugs and cost

| Pipeline | bugs | without output (per run) | front-end calls / bug (bugs with output) | tokens / bug (bugs with output) | judge calls / bug (all bugs) |
|---|---:|---|---:|---:|---:|
| SoapFL | 388 | 29 | 11.5 | 28,970 | - |
| SoapFL + judge | 388 | 29 | 11.5 | 28,970 | 8.2 |
| Class widening (always) | 388 | 19 | 31.1 | 76,674 | - |
| Class widening (always) + judge | 388 | 19 | 31.1 | 76,674 | 17.5 |
| Class widening (gated) | 388 | 23 | 19.4 | 47,949 | - |
| Class widening (gated) + judge | 388 | 23 | 19.4 | 47,949 | 12.2 |

## Paired test against plain SoapFL (Top-1, exact McNemar on the median run of each pipeline)

One main comparison per research question (RQ1, RQ2, RQ3; this choice of main comparisons is Claude's proposal of 2026-11-09 and must be confirmed by the user before the official runs); the others are exploratory and their p-values are Holm-corrected. 'Runs with a gain' = in how many run pairs (run i vs run i of SoapFL) the pipeline gained more bugs than it lost.

| Pipeline vs SoapFL | role | median run used | gained / lost | p | p (Holm) | runs with a gain |
|---|---|---:|---:|---:|---:|---:|
| SoapFL + judge | RQ3 | 1 | +43 / -10 | 5.55e-06 | - | 1 of 1 |
| Class widening (always) | RQ1 | 1 | +21 / -12 | 0.163 | - | 1 of 1 |
| Class widening (always) + judge | exploratory | 1 | +65 / -19 | 4.75e-07 | 9.5e-07 | 1 of 1 |
| Class widening (gated) | RQ2 | 1 | +28 / -20 | 0.312 | - | 1 of 1 |
| Class widening (gated) + judge | exploratory | 1 | +57 / -21 | 5.57e-05 | 5.57e-05 | 1 of 1 |

## How many bugs change between runs (Top-1 hit or not)

| Pipeline | run pair | bugs that flip |
|---|---|---:|
