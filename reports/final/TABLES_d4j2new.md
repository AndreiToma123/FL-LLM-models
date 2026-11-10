# Defects4J 2.0 new bugs: results over 1 run(s)

Judge = selector S8a+S2 replayed on each run's own candidate lists. Every bug counts; a bug without output is a miss. Median and range (min-max) over the runs that exist.

## Top-1

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 104 | 104 | 104-104 |
| SoapFL + judge | 138 | 138 | 138-138 |
| Class widening (always) | 117 | 117 | 117-117 |
| Class widening (always) + judge | 145 | 145 | 145-145 |
| Class widening (gated) | 111 | 111 | 111-111 |
| Class widening (gated) + judge | 143 | 143 | 143-143 |

## Top-3

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 163 | 163 | 163-163 |
| SoapFL + judge | 170 | 170 | 170-170 |
| Class widening (always) | 189 | 189 | 189-189 |
| Class widening (always) + judge | 207 | 207 | 207-207 |
| Class widening (gated) | 177 | 177 | 177-177 |
| Class widening (gated) + judge | 187 | 187 | 187-187 |

## Top-5

| Pipeline | run 1 | median | range |
|---|---:|---:|---:|
| SoapFL | 177 | 177 | 177-177 |
| SoapFL + judge | 178 | 178 | 178-178 |
| Class widening (always) | 215 | 215 | 215-215 |
| Class widening (always) + judge | 221 | 221 | 221-221 |
| Class widening (gated) | 202 | 202 | 202-202 |
| Class widening (gated) + judge | 205 | 205 | 205-205 |

## Bugs and cost

| Pipeline | bugs | without output (per run) | front-end calls / bug (bugs with output) | tokens / bug (bugs with output) | judge calls / bug (all bugs) |
|---|---:|---|---:|---:|---:|
| SoapFL | 444 | 21 | 11.5 | 24,033 | - |
| SoapFL + judge | 444 | 21 | 11.5 | 24,033 | 7.3 |
| Class widening (always) | 444 | 3 | 33.2 | 71,687 | - |
| Class widening (always) + judge | 444 | 3 | 33.2 | 71,687 | 20.2 |
| Class widening (gated) | 444 | 3 | 26.7 | 56,612 | - |
| Class widening (gated) + judge | 444 | 3 | 26.7 | 56,612 | 15.0 |

## Paired test against plain SoapFL (Top-1, exact McNemar on the median run of each pipeline)

One main comparison per research question (RQ1, RQ2, RQ3; this choice of main comparisons is Claude's proposal of 2026-11-09 and must be confirmed by the user before the official runs); the others are exploratory and their p-values are Holm-corrected. 'Runs with a gain' = in how many run pairs (run i vs run i of SoapFL) the pipeline gained more bugs than it lost.

| Pipeline vs SoapFL | role | median run used | gained / lost | p | p (Holm) | runs with a gain |
|---|---|---:|---:|---:|---:|---:|
| SoapFL + judge | RQ3 | 1 | +42 / -8 | 1.16e-06 | - | 1 of 1 |
| Class widening (always) | RQ1 | 1 | +30 / -17 | 0.0789 | - | 1 of 1 |
| Class widening (always) + judge | exploratory | 1 | +61 / -20 | 5.66e-06 | 5.66e-06 | 1 of 1 |
| Class widening (gated) | RQ2 | 1 | +27 / -20 | 0.382 | - | 1 of 1 |
| Class widening (gated) + judge | exploratory | 1 | +53 / -14 | 1.77e-06 | 3.55e-06 | 1 of 1 |

## How many bugs change between runs (Top-1 hit or not)

| Pipeline | run pair | bugs that flip |
|---|---|---:|
