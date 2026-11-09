# How to fact-check the thesis proposal by hand

This guide lists every number in the Master Thesis Proposal, says which file it comes from, and shows how to check it yourself. There are two ways:

- **Quick way (5 minutes):** run one script that recomputes almost everything, then compare its printout with the doc.
- **By hand:** open each file, find the row named below, and compare. For p-values and 95% ranges there are short recipes at the end.

Do the quick way first, then check by hand a few numbers from each section. If the hand checks match, you can trust the script for the rest.

## 1. Before you start

What you need:

1. **The repository on your PC:** `D:\Github\FL-LLM-models`. The 8 full CSC runs are in `reports\`:

   | Short name | Dataset 1 (388 bugs, Defects4J 1.4) | Dataset 2 (444 new bugs, Defects4J 2.0) |
   |---|---|---|
   | SoapFL | `runall-qwen25coder-csc` | `runall-qwen25coder-d4j2new-csc` |
   | Class widening, always | `runall-qwen25coder-ca3-csc` | `runall-qwen25coder-ca3-d4j2new-csc` |
   | Class widening, gated | `runall-qwen25coder-ca3g-csc` | `runall-qwen25coder-ca3g-d4j2new-csc` |
   | HypoDeduce | `runall-qwen25coder-hd-h5c5m3-csc` | `runall-qwen25coder-hd-h5c5m3-d4j2new-csc` |

2. **The judge (selector) results:** `reports\judge-vllm\`. The files for the 6 SoapFL and class-widening runs are already there. **The HypoDeduce judge files are not on your PC**; they are in the archive `judge-hd.tgz` on your laptop. Unpack it into `reports\judge-vllm\` on the PC (you can copy it over with a USB stick or a cloud folder, then run `tar -xzf judge-hd.tgz -C reports\judge-vllm` from the repository folder). Without them, every "HypoDeduce + selector" number cannot be checked.
3. **MyCSC** (my.csc.fi → project 2021789 → billing) for the total billing units.
4. **The PDFs** of SoapFL and HypoDeduce (in the project files) for the numbers quoted from the papers.
5. **Python 3** (already on your PC) for the script and for the two one-line formulas at the end.

## 2. The counting rules (read this first, or nothing will match)

- **Top-N:** a bug counts as found at Top-N if a real buggy method is at place N or better in the final ranking. Top-1 = it is first.
- **Every bug counts.** Dataset 1 always has 388 bugs and dataset 2 always 444. A bug where the run crashed or gave no ranking counts as *not found*. So a Top-1 of 130 means 130 out of 388, not 130 out of the bugs that worked.
- **"Reaches the ranking" (recall):** the buggy method is anywhere in the final list.
- **Paired comparison of A and B:** look only at bugs where exactly one of the two is right. *Gained* = B right, A wrong. *Lost* = A right, B wrong. The p-value comes only from these two counts (recipe in section 5). Bugs both get right or both get wrong do not matter.
- **In `per_bug.csv`:** the column `method_rank` holds the place of the first real buggy method. `N/A` (or an empty cell, or a missing bug) means *not found*.

## 3. The quick way: run the script

From the repository folder:

```
python scripts\factcheck_proposal.py
```

It only reads files; it changes nothing. For each dataset it prints:

- the `ALL` row of each run's `summary.md` (Top-1/3/5, buggy method reached, tokens per bug),
- model calls per bug and each CSC job with minutes and billing units,
- SoapFL's Top-1 with its 95% range,
- every paired comparison used in the proposal, as `Top-1 130 vs 152 (+31/-9, p=0.001)` = A's count, B's count, bugs gained by B, bugs lost by B, p-value,
- for dataset 1, the 288 bugs never used to design the selector.

If the HypoDeduce judge files are missing it prints "data missing" for those lines instead of failing.

## 4. The checklist: every number, where it is, how to check

Section numbers are those of the proposal. "summary" = `reports\<run>\summary.md`, row `| ALL |`; its columns are: Attempted (all bugs), With output, Top-1, Top-3, Top-5, Class hit (right class chosen), Tokens/bug. "funnel" = `reports\<run>\funnel.md`.

### 4.1 Headline results of each pipeline (used in the abstract, 4.2, 6.2, 8.1, 9.1)

| What | Dataset 1 | Dataset 2 | Where to look |
|---|---|---|---|
| SoapFL Top-1 / 3 / 5 / reached | 130 / 191 / 199 / 207 | 110 / 167 / 178 / 189 | summary of the SoapFL run. Note: summary.md has no "reached" column; its `Class hit` column (246 / 235) counts bugs where the right *class* was chosen. The 207 / 189 is in `funnel.md`, row `buggy method reached ranking` (or `ties.md`, line "buggy method present in the ranking") |
| Class widening (always) | 134 / 206 / 234 / 259 | 107 / 191 / 213 / 253 | summary of the `ca3` run; "reached" from its `funnel.md` |
| Class widening (gated) | 124 / 200 / 215 / 240 | 118 / 186 / 206 / 236 | summary of the `ca3g` run; "reached" from its `funnel.md` |
| HypoDeduce | 127 / 196 / 213 / 253 | 119 / 188 / 219 / 279 | summary of the `hd-h5c5m3` run; "reached" from its `funnel.md` |
| Tokens per bug | 26.5k, 73.3k, 46.9k, 186k | 22.5k, 70.7k, 56.1k, 167k | last column of the summary `ALL` row (SoapFL, always, gated, HypoDeduce) |
| Model calls per bug | 11, 31, 20, 93 | 11, 33, 27, 101 | `per_bug.csv`: average of `llm_calls` over rows with `has_result` = True (Excel: filter, then the status bar shows the average) |
| "Eight to nine times as many model calls" (abstract, 6.2, 9.1) | 93 / 11 = 8.5 | 101 / 11 = 9.2 | the model calls row above. By tokens the factor is only about 7 (186k / 26.5k), so the sentence must keep saying "model calls" |

### 4.2 Ties (7.1 table and 2.2)

File: `reports\<run>\ties.md`, table "Top-N under different orders inside tie groups".

| Number | Row in ties.md |
|---|---|
| Random tie order (SoapFL d1: 121.1, 95% range 112–131) | `random (mean of 2000 draws)` and `random, 95% range` |
| Perfect tie-breaker (SoapFL d1: 187 / 206 / 207) | `best case … = oracle tie-breaker` |
| Worst case (84) | `worst case` |
| "210 of 352 bugs have a tied top score" | bullet `bugs whose highest score is shared by several methods` |

The random row in `judge-vllm\<run>-selection.md` (120.9) comes from a separate draw of 2000 random orders, so it differs by a few tenths. Either is fine; make sure the doc uses one of them consistently.

### 4.3 Selector results (5.2, 7.1)

File: `reports\judge-vllm\<run>-selection.md`, first table ("all"). One row per selector (S0, S1, S6, S5, S5+S2, S8a, S8a+S2). Columns: Top-1, Top-3, Top-5, then "Top-1 vs source" (bugs gained minus lost) and the McNemar p for Top-1 against the run without a selector.

| Number | Where |
|---|---|
| SoapFL + S8a+S2: 152 (d1), 137 (d2) | row `S8a+S2` of `runall-qwen25coder-csc-selection.md` / `…-d4j2new-csc-selection.md` |
| Class widening + S8a+S2: 172 (d1), 142 (d2) | row `S8a+S2` of the `ca3` selection files |
| Gated + S8a+S2: 158 (d1), 145 (d2) | row `S8a+S2` of the `ca3g` selection files |
| HypoDeduce + S8a+S2: 152 / 148; S5: 164 / 155 | rows `S8a+S2` and `S5` of the `hd-h5c5m3` selection files (from judge-hd.tgz) |
| Gate S0 > S6 > S8a+S2 (SoapFL d1: 152, 5.9 calls per bug) | row `S0 > S6 > S8a+S2` of `<run>-gate.md` |

### 4.4 Paired p-values (4.2, 5.2, 6.2, 8.1)

All come from the script's "Paired tests" lines. To check one by hand, take the *gained* and *lost* numbers from the script line and use the recipe in 5.1.

| Comparison | Dataset 1 | Dataset 2 |
|---|---|---|
| Class widening (always) vs SoapFL, Top-1 / 3 / 5 | 0.67 / 0.082 / <0.001 | 0.76 / 0.001 / <0.001 |
| Gated vs SoapFL, Top-1 / 3 / 5 | 0.43 / 0.24 / 0.033 | 0.32 / 0.014 / <0.001 |
| SoapFL + selector vs SoapFL, Top-1 | 130 → 152 (+31/−9), p = 0.0007 | 110 → 137 (+39/−12), p < 0.001 |
| Class widening + selector vs SoapFL + selector, Top-1 | 152 vs 172 (+40/−20), p = 0.013 | 137 vs 142 (+33/−28), p = 0.61 |
| Gated + selector vs SoapFL + selector, Top-1 | 152 vs 158, p = 0.47 | 137 vs 145, p = 0.36 |
| HypoDeduce vs SoapFL, Top-1 | 130 vs 127 (+33/−36), p = 0.81 | 110 vs 119 (+40/−31), p = 0.34 |
| HypoDeduce vs SoapFL, Top-3 / Top-5 / reached | 0.65 / 0.14 / <0.001 | 0.014 / <0.001 / <0.001 |
| HypoDeduce vs class widening, Top-1 / Top-5 / reached | 0.49 / 0.006 / 0.50 | 0.17 / 0.60 / 0.009 |
| HypoDeduce + selector vs HypoDeduce, Top-1 | 127 → 152, p = 0.004 | 119 → 148, p < 0.001 |
| HypoDeduce + selector vs SoapFL + selector | Top-1 152 vs 152; Top-3 p = 0.034; Top-5 p = 0.003 | Top-1 148 vs 137, p = 0.24 |
| HypoDeduce + selector vs class widening + selector, Top-1 | 152 vs 172, p = 0.013 | 148 vs 142, p = 0.56 |
| 288 held-out bugs, SoapFL vs SoapFL + selector, Top-1 | 102 → 116 (+22/−8), p = 0.016 | — |

Two values were changed on 2026-11-09 after this check: 0.014 → 0.013 (exact 0.0135) and 0.007 → 0.006 (exact 0.0065). They had been rounded up instead of to the nearest value.

**Checking a paired comparison without the script (SoapFL and class widening only).** Open both `per_bug.csv` files in Excel, put them side by side by `bug_id` (XLOOKUP), and add two columns: "A found" = `method_rank` is a number ≤ N, "B found" the same. Count the rows where only B is found (gained) and only A is found (lost). This works for any two of the 8 runs; it does not work for the selector results, which have no `per_bug.csv`, so use the script for those.

### 4.5 The 95% ranges (2.2, 4.2)

Example: SoapFL Top-1 on dataset 1 is 130/388 = 33.5%, range 29.0% to 38.3%. Recipe in 5.2. Check any range in the doc the same way, with its count and 388 or 444.

### 4.6 Class widening details (4.2)

| Number | Where |
|---|---|
| Offline study on 352 / 407 bugs; SoapFL alone picks the right class in 68% / 54%; SoapFL's class plus the top 3 = 88% / 74% | This study was computed once, outside the pipeline, and has no result file. Its numbers are written down in `claude/ROADMAP.md` (paragraph "Offline class-recall study"). Partial cross-check: SoapFL `funnel.md`, row `right class selected` = 246 of 360 bugs with output = 68% on dataset 1 |
| Actual right-class rate with widening | `funnel.md` of the `ca3` and `ca3g` runs, row `right class selected` |
| "Gated keeps 46% to 80% of the gain at 45% to 73% of the extra model calls" | Gain share = (gated − SoapFL) ÷ (always − SoapFL) for Top-5 and reached, e.g. d1 Top-5 (215−199)÷(234−199) = 46%. Call share = (gated calls − 11) ÷ (always calls − 11), e.g. d1 (20−11)÷(31−11) = 45%, d2 (27−11)÷(33−11) = 73% |

### 4.7 Cost and budget (3.2, 7.2)

| Number | Where |
|---|---|
| Billing units of each job | `reports\<run>\job_meta.json`, field `gpu_billing_units_est` (the script prints them). Formula: minutes ÷ 60 × 200 |
| HypoDeduce judge jobs 18.0, 22.4 and 3.4 BU | `reports\judge-vllm\<run>-judge-job.json` (from judge-hd.tgz) |
| HypoDeduce d1 jobs ≈ 1,459 BU (1239.8 + 208.2 + 10.8) + about 80 BU for the cancelled job 2720333 | `job_meta.json` of the HypoDeduce d1 run. Job 2720333 is not in any file; check it in MyCSC or with `sacct -j 2720333` on Roihu |
| Total 2,499 BU used | MyCSC → project 2021789 → billing |
| "About 1,400 lost to setup problems; a clean study costs about 1,100" | Add up the `gpu_billing_units_est` of the jobs listed in section 3 of the script printout plus the judge jobs; that sum is the clean cost. 2,499 minus that sum is the lost part. The Math-14 hang is the 1,239.8 BU job 2706305 (371 minutes) |
| 54 BU (3.2) | SoapFL d2 job 2532213: 53.6 BU in its `job_meta.json` |

Remember: CSC bills the reserved GPU time from start to end of the job (200 BU per GPU-hour), not how hard the GPU worked. A job that hangs for 6 hours costs 6 hours.

### 4.8 Numbers quoted from the papers (6.2 paper table, 3.3)

| Number | Where |
|---|---|
| HypoDeduce paper results | Results table of the HypoDeduce PDF (project files). Check the model, dataset and Top-N match the row they are compared with in the doc |
| SoapFL paper results | Results table of the SoapFL PDF |
| References | SoapFL: IEEE Transactions on Software Engineering 51(4), 1173–1187, doi 10.1109/TSE.2025.3543187. FaR-Loc: arXiv:2509.20552 (preprint, no journal yet). HypoDeduce authors: Le, M. T., Zheng, X., and Kang, H. J. |

## 5. Recipes

### 5.1 p-value from gained and lost (exact McNemar test)

You only need the two counts. Example: SoapFL + selector vs SoapFL on dataset 1, gained 31, lost 9.

The idea: if the two pipelines were equally good, each of the 40 disagreeing bugs would be a coin flip. The p-value is how likely a split as uneven as 31 to 9 (or more) is with a fair coin, counting both directions.

Python (paste into a terminal, replace 31 and 9):

```
python -c "from math import comb; b,c=31,9; n=b+c; print(min(1,2*sum(comb(n,i) for i in range(min(b,c)+1))/2**n))"
```

Prints 0.00068 → reported as p = 0.0007.

Without Python: any online "binomial test" calculator with number of trials = 40 (gained + lost), successes = 9 (the smaller one), probability 0.5, two-sided. Do not use a "chi-square McNemar" calculator; it gives a slightly different number because it is an approximation.

How to read it: below 0.05 = the difference is unlikely to be luck. Above 0.05 = could be luck, so the doc says "no clear difference".

### 5.2 95% range of a percentage (Wilson interval)

Example: 130 found out of 388.

```
python -c "k,n,z=130,388,1.96; p=k/n; c=p+z*z/(2*n); h=z*((p*(1-p)/n+z*z/(4*n*n))**0.5); d=1+z*z/n; print(round(100*(c-h)/d,1), round(100*(c+h)/d,1))"
```

Prints 29.0 38.3. Online: any "Wilson score interval" calculator with successes 130 and trials 388.

## 6. If something does not match

1. Check the counting rules (section 2): most mismatches come from dividing by the bugs with output instead of all bugs, or from using the `Class hit` column of `summary.md` (right class) instead of `funnel.md` row `buggy method reached ranking` (right method).
2. Check you opened the right run folder: `ca3` is always, `ca3g` is gated; `-d4j2new` is dataset 2.
3. Check rounding: the doc rounds p-values to two significant digits, to the nearest value.
4. If it still does not match, the doc is wrong: fix the doc, and note the change in `claude/ROADMAP.md`.
