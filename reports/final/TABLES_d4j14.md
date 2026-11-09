# Defects4J 1.4.0: results over 1 run(s)

Judge = selector S8a+S2 replayed on each run's own candidate lists. Every bug counts; a bug without output is a miss. Median and range (min-max) over the runs that exist.

## Top-1

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 130 | 130 | 130-130 |
| SoapFL + judge | 152 | 152 | 152-152 |
| Class widening (always) | 134 | 134 | 134-134 |
| Class widening (always) + judge | 172 | 172 | 172-172 |
| Class widening (gated) | 124 | 124 | 124-124 |
| Class widening (gated) + judge | 158 | 158 | 158-158 |

## Top-3

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 191 | 191 | 191-191 |
| SoapFL + judge | 195 | 195 | 195-195 |
| Class widening (always) | 206 | 206 | 206-206 |
| Class widening (always) + judge | 225 | 225 | 225-225 |
| Class widening (gated) | 200 | 200 | 200-200 |
| Class widening (gated) + judge | 214 | 214 | 214-214 |

## Top-5

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 199 | 199 | 199-199 |
| SoapFL + judge | 201 | 201 | 201-201 |
| Class widening (always) | 234 | 234 | 234-234 |
| Class widening (always) + judge | 242 | 242 | 242-242 |
| Class widening (gated) | 215 | 215 | 215-215 |
| Class widening (gated) + judge | 222 | 222 | 222-222 |

## Bugs and cost

| Pipeline | bugs | without output (per run) | model calls / bug | tokens / bug | judge calls / bug |
|---|---:|---|---:|---:|---:|
| SoapFL | 388 | 28 | 11.4 | 28,343 | - |
| SoapFL + judge | 388 | 28 | 11.4 | 28,343 | 7.3 |
| Class widening (always) | 388 | 21 | 31.4 | 77,076 | - |
| Class widening (always) + judge | 388 | 21 | 31.4 | 77,076 | 17.9 |
| Class widening (gated) | 388 | 20 | 19.9 | 49,158 | - |
| Class widening (gated) + judge | 388 | 20 | 19.9 | 49,158 | 13.2 |

## Paired test against plain SoapFL (Top-1, exact McNemar on the median run of each pipeline)

One main comparison per research question (RQ1, RQ2, RQ3); the others are exploratory and their p-values are Holm-corrected. 'Runs with a gain' = in how many run pairs (run i vs run i of SoapFL) the pipeline gained more bugs than it lost.

| Pipeline vs SoapFL | role | median run used | gained / lost | p | p (Holm) | runs with a gain |
|---|---|---:|---:|---:|---:|---:|
| SoapFL + judge | RQ3 | 1 | +31 / -9 | 0.00068 | - | 1 of 1 |
| Class widening (always) | RQ1 | 1 | +26 / -22 | 0.665 | - | 1 of 1 |
| Class widening (always) + judge | exploratory | 1 | +62 / -20 | 3.71e-06 | 7.43e-06 | 1 of 1 |
| Class widening (gated) | RQ2 | 1 | +17 / -23 | 0.43 | - | 0 of 1 |
| Class widening (gated) + judge | exploratory | 1 | +46 / -18 | 0.000617 | 0.000617 | 1 of 1 |

## How many bugs change between runs (Top-1 hit or not)

| Pipeline | run pair | bugs that flip |
|---|---|---:|
