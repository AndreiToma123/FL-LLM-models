# Frozen configuration for the official runs (DRAFT, 2026-11-09)

**Status: DRAFT. It becomes binding when the user commits it and tags the commit `final-config`**
(`git tag final-config && git push origin final-config`). After the tag nothing below may change; every official
job records its `git_commit` in `job_meta.json`, so a run made with other code can be found.

All values were read from the code and the existing run files on 2026-11-09 (see `docs/AUDIT_2026-11-09.md`).

## Model and serving
- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`, bf16 (not quantized), weights from Hugging Face via `csc/setup.sh model`
  (the revision is now written to `job_meta.json` as `model_weights_id`).
- Server: vLLM module `python-vllm/0.29.0` on one GH200 (Roihu), `--max-model-len 16384`, `--seed 0`,
  `--gpu-memory-utilization 0.90`, `--max-num-seqs 64`.
- Sampling: temperature 0 (greedy) everywhere; SoapFL answers up to 3,072 tokens; judge answers 1-2 tokens.

## SoapFL (baseline, frozen since tag `soapfl-baseline-v1`)
- SoapFL commit c9f75f4f34 + `patches/0001-open-model-support.patch` (digest f305e1247c469785), config `Default`
  (at most 5 failing test classes and 5 failing tests per class), lenient answer parsing.
- Seed: run r uses SoapFL seed r - 1 (`csc/submit.sh --rep r`).

## Class widening (RQ1 always, RQ2 gated)
- `fl_tools/classaug.py`, digest 4aa3d13b0b7b1758: k = 3 classes from the free class ranking (stack position, name
  overlap with the failing test, failing tests covering, number of executed methods, name), only classes SoapFL
  offered to its model; test classes never added. Gated = only when SoapFL's class is not the ranking's first.

## Judge (RQ3)
- **Main selector: S8a+S2** (frozen on 2026-10-25, before any test result; roadmap 4i). Shortlist: the tied top
  group, at most K = 8 methods. Pairwise in both orders, Copeland score, failure-context evidence; candidates still
  tied are ordered by the expected 0-9 score from log-probabilities. Prompt versions 239089a8c86f (S5, S5+S2) and
  75b2b186403e (S8a, S8a+S2).
- Also reported (secondary): S5, S5+S2, S8a, S6, S1 and the gate S0 > S6 > S8a+S2 (margin 0.5).
- Decided by the user 2026-11-09: S8a+S2 stays the main selector; testing the other selectors as main (for example
  plain S5) is future work. The judge job still writes the other selectors' results, for that future work.

## Run protocol
- **One run per setting and dataset (`--rep 1`; user decision 2026-11-09)**, all with the same code version; no reruns
  of failed bugs (`--retries 0`, no `--retry-failed`); a failed bug is a miss and is listed with its reason. All old
  SoapFL / class-widening results on datasets 1 and 2 are replaced by these runs.
- Report dataset 1 twice: all 388 bugs, and the 288 bugs outside the 100-bug design sample of
  `configs/selection_split.json` (`analyze.py tables --heldout`; computed from the same runs, no separate run).
- Main comparison per research question (confirmed by the user 2026-11-09): RQ1 always vs SoapFL, RQ2 gated vs
  SoapFL, RQ3 SoapFL + S8a+S2 vs SoapFL (Top-1, exact McNemar); all others exploratory, Holm-corrected.
- Safeguards: 1 h per bug; stuck-bug guard 3 x p95 (at least 10 min) once all bugs started; circuit breaker at more
  than 50% failures after 30 attempts; judge questions give up after 120 s; Slurm limits 4 h (front end), 2 h (judge).
- Counting: every bug of the dataset counts; no output = miss. Top-1/3/5, MRR; exact McNemar on the median run.

## Not part of the official runs
- HypoDeduce (archived), FlexFL, Ochiai / stack-trace baselines (future work), the agent selector S8b.
