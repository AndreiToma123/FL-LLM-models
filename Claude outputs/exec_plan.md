# Roadmap addendum 2026-11-09 (section 15): execution plan for the coder agent (append to ROADMAP.md after section 14)

### UPDATE 2 - 2026-11-09 (night): new datasets chosen, Ochiai moved to future work. This block overrides the older blocks and plan phases B and D where they differ.

**Decisions (user):**
1. **Use BOTH GHRB and GitBug-Java as extra test datasets** (this reverses the 2026-10-25 rejection, roadmap 3k).
2. **The Ochiai and stack-trace baselines (old phase B1-B4) are left for later** and go into the thesis "future work" section. Phase B0 (freeze the settings and tag them in git) stays and is still required before any new-dataset run.

**Facts checked on 2026-11-09 (read-only, arXiv abstract pages only; the papers were not read in full):**
- GHRB ("GitHub Recent Bugs", arXiv 2310.13229): 76 real Java bugs, collected after the OpenAI data cut-off; FlexFL used 28 of them that could be reproduced (FlexFL PDF).
- GitBug-Java (arXiv 2402.02961): 199 bugs from 55 open-source projects, taken from the 2023 commit history; each bug comes with a reproducible environment. The abstract does not say which tools build that environment (not checked).

**Important correction to the older plan (leakage):** both sets are "recent", but recent is not the same as "unseen by Qwen". Qwen2.5-Coder was released in September 2024 and its training-data cut-off is not stated in this project. GitBug-Java bugs are from 2023, so they are BEFORE the model's release and may have been in its training data. GHRB's cut-off is OpenAI's, not Qwen's. So: do NOT call either set "leakage-free" in the thesis. Write "more recent than Defects4J (2014-2022)". The earlier sentence "use only bugs dated clearly after the model's release" cannot be met by GitBug-Java; replace it by: record the date of every bug, use all usable bugs, and report results by date if the dates allow it.

**What the coder must do (replaces phase D):**
1. **Feasibility first, one set at a time, time-boxed (about one working day each).** Both sets are not Defects4J. Everything that is Defects4J-specific must be adapted: checking out the buggy version, running the failing tests, SoapFL's measuring tool (instrumentation), the failure-context export, the bug list, and the ground truth (the faulty methods, normally taken from the fixing change). Read why GHRB and GitBug-Java were rejected in roadmap 3k; the reason may be exactly this adaptation work. Write down what has to change; do NOT change the frozen SoapFL path (tag `soapfl-baseline-v1`): add a separate bug-source module and a `--dataset` value for each.
2. **Pilot of 10 bugs per set** (only after step 1 says it is possible): the bug builds, a failing test is found, the measuring tool works, class and method ground truth is derived and spot-checked by hand on 3 bugs.
3. **Smoke test and written report, then wait for the user's go** (as in the earlier update block).
4. **Run the FROZEN pipeline** (plain SoapFL, class widening always and gated, judge in both orders) once the freeze tag exists, 3 runs each, no tuning. Same safeguards as every other job (per-bug limit, stuck-bug guard, circuit breaker, skip known failures).
5. **Report by set, never merged with Defects4J.** The sets are small (GHRB at most 76, usually fewer that can be reproduced; GitBug-Java at most 199), so differences of a few bugs are noise. Present them as supporting evidence that the idea is not tied to Defects4J; the main numbers stay on datasets 1 and 2. Give counts of bugs that could not be reproduced, with the reason.
6. If one set cannot be made to work in the time box, say so with the reason and continue with the other. Do not drop silently.

**Ochiai in the thesis (future work wording, for the user to use):** "A classic test-based ranking (Ochiai) and a stack-trace-only ranking were not run as extra baselines. They would show whether class widening is better than a plain ranking, and would give a fairer link to FlexFL, which uses an Ochiai-type first step." **Honest note:** a partial answer exists already at class level: the free class ranking used by class widening (stack position, coverage) alone puts the right class first in 62% (dataset 1) and 50% (dataset 2) of the bugs studied, against 68% / 54% for SoapFL's own first choice (roadmap 3l, offline study on 352 / 407 bugs); and the stack/coverage selector S6 was measured (roadmap 4l). Neither is Ochiai.

**Open questions for the user:** (a) the time box per dataset; (b) if both sets work, whether the final tables show them as a third and fourth column or in a separate short chapter.

---

### UPDATE 2026-11-09 (evening): the user's decisions and thinking, in plain words. This block OVERRIDES the older text of this plan where they differ.

**What the user said (shortened, his reasoning kept):**
1. The work already fixes several weaknesses of SoapFL and does something new: SoapFL run with an open model. This may be a research gap. **NOT checked yet** (nobody has looked for earlier SoapFL runs with small open models; FlexFL uses open models but a different design).
2. **HypoDeduce is removed completely**, except as a cited inspiration. Reasons given: (a) the re-implementation is not an exact reproduction, so comparing it with SoapFL is not fair; (b) the authors' repository has no licence; (c) the numbers printed in its paper come from a different, closed model (GPT-4o), so they are not a reliable comparison either.
3. **FlexFL is not tackled** (the work went in a different direction, with SoapFL). It is fine as long as the 3 research questions are answered; the teacher will give feedback if something is wrong.
4. **Top priorities now:** (i) choose a different dataset; (ii) check the code for problems; (iii) re-run anything inconsistent; (iv) run the experiments several times, as proposed in the review; (v) confirm the safety measures that stop a broken or stuck bug from running for hours are still on for EVERY experiment; (vi) run a smoke test first and analyse it before anything bigger.

**Notes by Claude on these decisions (so the thesis stays honest):**
- *HypoDeduce licence:* no code was copied (the roadmap, section 3c, records that the re-implementation was written from the paper). So the licence is a weaker reason than fairness; the strong reason is (a) and (c). In the thesis write: "inspired by HypoDeduce (Le et al., 2026); not reproduced, because the paper gives no prompts or scoring rules and the authors' code has no licence". Do not write that the re-implementation "does not work".
- *Using its paper's numbers:* only as context in a separate column "reported by the authors", with the model named. No significance test against them.
- *What disappears from the proposal:* chapter 6, the HypoDeduce columns in chapter 7, the HypoDeduce part of the abstract, discussion and conclusions, the "about a third of HypoDeduce's calls" claim, and the HypoDeduce runs from the budget table. The 3 RQs (class widening, gated widening, final selection by a judge) do not depend on HypoDeduce, so they stay. The old HypoDeduce files are archived, not deleted.
- *FlexFL stays in the text:* related work and the limitations table must still say what FlexFL did (open models, Ochiai-type first step) and why this work differs. Not testing it is a choice that must be written down, not left out.
- *Ochiai / stack-trace baselines (phase B):* still recommended, but because of RQ1 (is class widening better than a plain ranking?), not because of FlexFL. B3 ("Ochiai + judge") is optional. The user has not decided on B yet.
- *Why a new dataset:* the judge and class-widening settings were chosen on dataset 1, and dataset 2 is the same benchmark family (Defects4J). A dataset from another source tests that the idea is not tied to Defects4J. The 2026-10-25 decision rejected GHRB and GitBug-Java; the reason is not in the notes found so far, so this decision is REOPENED by the user.

**Revised order of work (replaces the phase order of 15.2-15.5):**
1. **Code audit (no GPU).** Re-read the changes made since the last full run. List problems (not fix silently): judge asks both orders (A1), what "one call" means (A2), settings sheet (A3), the 7 missing bugs and the failed bugs (A5), per-bug result files (A6).
2. **Safety-measure audit (no GPU).** For EACH kind of job (SoapFL, class widening gated/always, judge replay, new-dataset runs) write one line: is the per-bug time limit on, is the stuck-bug guard (tail guard) on, is the circuit breaker (run stops itself when more than half of the bugs fail) on, are final failures skipped on resume? Known from the roadmap (section 4n): these were built into `fl_tools/runner.py` and passed through `csc/submit.sh`. To check, not assume: that the judge job (`csc/submit_select.sh`) has an equivalent limit on a stuck call; that `--retry-failed` is NOT switched on by default in `submit.sh` (it would undo the skip rule); that the values (1 h per bug, 3x the 95th-percentile tail, 50% failure rate after 30 attempts) are what the jobs really receive. Test the guards with a fake slow bug and a fake failing set on the mock server. Output: a table "job type x safeguard x on/off x how checked".
3. **Smoke test, then analysis, then a stop.** 5 bugs per dataset (old datasets and the new one) through the whole pipeline on Roihu. Analyse before going on: every bug has a per-bug file; judge logs show both orders; time and billing units per bug match the estimate; no guard fired by accident; failures are the expected kinds only (the known `no_failing_test_output` Mockito cases). Write the result in `SMOKE_REPORT.md` and WAIT for the user's go.
4. **New dataset.** Read why GHRB / GitBug-Java were rejected (roadmap 3k). Then a 10-bug pilot of the best candidate (checks in 15.5). Use only bugs dated clearly after the model's release (Qwen's training cut-off is not stated in this project). If the pilot fails, report; dataset 2 stays the held-out test and the thesis says so.
5. **Freeze, then official runs** (15.3 B0, 15.4 C): tag `final-config`, rerun everything inconsistent, plain SoapFL / class widening / judge, 3 runs each, one script version, on Roihu.
6. **No HypoDeduce runs. No FlexFL runs.**
7. Billing units: estimate before each job, stop and report above 6,000 total (about 2,499 used).

**Open for the user:** which new dataset (decision after the pilot report); whether to run the Ochiai / stack-trace baselines (B); who checks "SoapFL with an open model is new" (a literature search; not done).

---
(Older plan below; where it conflicts with the update above, the update wins.)

Written for a coder agent that has NOT seen the chat. Plain language on purpose. "Bug" = one Defects4J bug. "Top-1" = the real faulty method is ranked first. "Judge" = the step that compares two candidate methods in both orders (A then B, B then A) and keeps the one that wins.

## 0. Why this plan exists (the decisions behind it)
1. The thesis point is NOT "we beat every paper". It is: **a small open model (Qwen2.5-Coder-7B) loses many bugs at the first step (choosing the class) and at the last step (ties between methods); two cheap fixes (try several classes = "class widening"; compare candidates in both orders = "judge") recover a measured part of that loss.** Every experiment below must serve that sentence.
2. All new and all faulty experiments are run (again) on Roihu when it is back, so the final numbers are official. Nothing from before is mixed into the final tables unless it is checked and rerun.
3. The judge MUST ask both orders. If any saved judge run did not, that run is repeated.
4. The HypoDeduce re-implementation is dropped from the main comparison (it is only "paper-guided", not the authors' code). It stays as an inspiration in the text. No new HypoDeduce runs. Existing HypoDeduce files are archived, not deleted. (User decision 2026-11-09; see section 6 for the one risk to keep in mind.)
5. Cybersecurity is not a goal for now. Chatbot-based research is not a source.
6. Work that is only planned is fine in a proposal. Do not rush a half-checked number into a table.

## 1. Rules for the coder agent
- Read-only on the web. Never fill forms or press buttons on websites.
- Do not change the judge, the class-widening rule or any setting after looking at results from a NEW dataset. Freeze first (step B0), tag in git, then run.
- Every claim in a report must come with the file it came from. If a number cannot be traced to a per-bug file, mark it "unchecked".
- Before any Roihu job: estimate billing units (BU) from earlier job logs and write the estimate in the job note. Project `project_2021789` has 10,000 GPU BU; about 2,499 were used (roadmap). Stop and report if a plan would pass 6,000 total.
- Report in plain language, no jargon, one short table per question.

## 2. Phase A - checks that need no GPU (start now, Roihu not needed)
A1. **Judge order check (highest priority).** Read the judge code. (a) Write a test with the mock server that proves every candidate pair produces TWO requests, one per order. (b) Scan every saved judge log: for each pair, are both orders present? Output: number of pairs, number missing an order, list of affected runs. If the number is above zero, those runs go on the rerun list (Phase C).
A2. **Define "one model call"** in `docs/` and in the cost table: count every single question sent to the model (so a pair judged in both orders = 2 calls). Recompute the cost table (calls per bug for SoapFL, class widening, judge, total). The old claim "class widening needs about a third of HypoDeduce's calls" is dropped with HypoDeduce.
A3. **Settings sheet** (one table, goes into the thesis): checkpoint name, base or instruct, bf16 non-quantized, sampling settings (temperature etc.), seed, vLLM version, context limit, git commit/tag, where the prompts are.
A4. **Which bugs fixed the cut-off of 3 classes?** Find in the roadmap/logs which data was used. Recompute class recall for k = 1, 2, 3, 4, 5 on dataset 1 and dataset 2 and report both. (If k = 3 was chosen on dataset 1 only, dataset 2 is the honest test of it.)
A5. **Bug bookkeeping.** (a) Name the 7 bugs in the 395-vs-388 gap and why they are out. (b) For the "seven failed bugs" re-run: bug ids, error, result of the re-run; where are the other five. (c) Explain 15 vs 18 Mockito bugs that did not run.
A6. **Per-bug results file** for every final run: bug id, rank of the true method (or "not found"), class right yes/no, calls used. From it compute Top-1/3/5, MRR (average of 1/rank) and average rank.

## 3. Phase B - cheap baselines (CPU only; Defects4J coverage runs; may run in the Docker image before Roihu returns)
What Ochiai is: a classic, non-AI formula. For each method, count how many FAILING tests run it and how many PASSING tests run it. A method run by all failing tests and by few passing tests gets a high score: `score = failed(m) / sqrt(total_failed * (failed(m) + passed(m)))`. It needs coverage data of ALL tests (not only the failing ones). Defects4J can produce coverage (verify the exact command in its docs; do not guess). FlexFL uses Ochiai-type scores as its first step to cut a project down to 20 methods.
B0. **Freeze.** Write `FROZEN_CONFIG.md`: SoapFL settings, class widening (always and gated, k), judge version. Git tag `final-config`. After this tag nothing in these parts changes.
B1. **Ochiai baseline** on dataset 1 and dataset 2: Top-1/3/5/MRR at method level, and class recall (is the true class among the top 1/3/5 classes by best method score?). Compare with class widening's class recall. No model needed.
B2. **Stack-trace-only baseline** (classes in the failing stack trace in order): same numbers. This tells if class widening is more than reading the stack trace.
B3. **Ochiai top-20 + our judge** ("FlexFL-like first step, our last step"): take Ochiai's top 20 methods, run the judge. Reports Top-1/3/5. This is the fair way to answer "why not FlexFL's first step?". It is NOT FlexFL itself; call it "Ochiai + judge" everywhere.
B4. Optional cheap tie-baselines from the review: expected score from log-probabilities alone (S2 alone), a finer score scale. Only if time allows.
Output of Phase B: one table per dataset: plain SoapFL | Ochiai | stack trace | Ochiai + judge | class widening | class widening + judge (the last two come from Phase C).

## 4. Phase C - official runs on Roihu (when it is back)
Order matters; stop after each step and report.
C1. Smoke test: 5 bugs per dataset through the whole pipeline; confirm the per-bug file and the two-order judge logs are written.
C2. Plain SoapFL, class widening (always), class widening (gated), on dataset 1 (388) and dataset 2 (444), ONE script version, **3 runs each** (different seeds). Report each run and the mean and spread.
C3. Judge on the saved candidate lists (cheap, repeat 3 times). Selectors to report: S5 (plain pairwise, both orders) as the simple main one, S5+S2 and S8a+S2 as extra. Name ONE selector as "main" BEFORE looking at dataset 2 numbers (use dataset 1 data only to choose, and write the choice into `FROZEN_CONFIG.md`).
C4. Anything on the rerun list from A1, A5. Nothing else is rerun.
C5. Held-out table: the 288 bugs not used for choosing settings (102 -> 116, 22 gained, 8 lost, p = 0.016 in the old run): recompute from the new runs, separate "judge alone" from "class widening + judge".
Statistics: one main comparison per research question (Top-1, paired, McNemar); all other comparisons marked "exploratory" and corrected (Holm). With 3 runs, also report how many bugs change between runs.

## 5. Phase D - a fresh dataset (so the method is not tested only on the data it was built on)
Facts checked: GHRB ("GitHub Recent Bugs", arXiv 2310.13229) has 76 real Java bugs collected after the OpenAI training cut-off; FlexFL used 28 reproducible ones. In this project GHRB and GitBug-Java were rejected on 2026-10-25 (reason in roadmap section 3k not seen by the writer - read it first; the likely issue is whether SoapFL's Java measuring tool works on them).
Careful: "after the OpenAI cut-off" does NOT mean "after Qwen2.5-Coder's training data ended". Qwen2.5-Coder came out in 2024; its exact data cut-off is not stated in this project. So: use only bugs whose fix date is clearly after the model's release, and write down the dates.
D1. Read why GHRB/GitBug-Java were rejected. If the reason is a tool problem, test whether it can be fixed in a day; if not, stop and report.
D2. Pilot on 10 bugs (no more). Check: bug builds, failing test found, SoapFL's measuring tool works, class and method ground truth can be derived.
D3. Only if the pilot passes: run the FROZEN pipeline once per setting on all usable bugs (expect a few dozen). No tuning. Report with the number of bugs and the dates.
D4. If it does not pass: say so; dataset 2 (Defects4J 2.0 new bugs, chosen before the selector was fixed) remains the held-out test and the thesis says exactly that.

## 6. Risks to keep in view
- Dropping HypoDeduce removes the only same-model comparison. In the old data HypoDeduce's version FOUND the faulty method more often (reach 279 vs 252 on dataset 2) but did not rank it first more often. Say this in the discussion; do not hide it.
- Comparing with numbers printed in other papers is context only: they used GPT-4o / gpt-3.5 / gpt-4.1-mini or 8B models of other families, other bug sets (395 bugs of v1.4.0, 381 of v1.2.0, 835 of v2.0.0) and their own code. Show those numbers in a separate column "reported by the authors", never in a significance test.
- "Newer model than FlexFL" is not a result. Qwen2.5-Coder-7B is newer than Llama3-8B, Qwen2-7B and Mistral-Nemo (release dates from general knowledge, not checked here) but nobody has shown it is better at fault localization. Do not write "better" without a same-pipeline test.
- Results come from one model family. A bigger judge (32B, fits one GH200) is optional, only after A-C are done.

## 7. Deliverables (files the coder returns)
1. `reports/final/JUDGE_ORDER_CHECK.md` (A1) 2. cost table (A2) 3. `SETTINGS.md` (A3) 4. class recall k=1..5 table (A4) 5. bug bookkeeping (A5) 6. per-bug result files + summary (A6) 7. Ochiai / stack-trace / Ochiai+judge tables (B) 8. final run tables with mean and spread (C) 9. pilot report and, if passed, dataset-D table (D) 10. `STATUS.md`: what is done, what is not, BU used.

## 8. Not decided yet (user)
Delete `RESEARCH_PROMPT.md` and `DEEP_RESEARCH_SYNTHESIS.md` (chatbot research): waiting for a yes. SieveFL: numbers unverified (page could not be opened here); do not cite. Sections 11, 13, 14 and this one are still not pasted into ROADMAP.md.
