# HypoDeduce re-implementation

Re-implementation of the method in

> Le, Zheng, Kang. *Abductive Reasoning for Neurosymbolic Fault Localization.* ICSE-NIER 2026, pp. 186-190.
> DOI 10.1145/3786582.3786836.

written **from the paper only**. No code or prompts were taken from the authors' repository (it has no
license). Wherever the paper does not specify a mechanism, the choice below is ours and is marked as such.
Cite the paper for the method; describe this as "a re-implementation from the paper's description".

## Where it lives

* `fl_tools/hypodeduce/` — the pipeline: `phases.py` (SoapFL phase classes), `logic.py` (parsing, retention,
  selection, ranking; unit-tested), `config/` (chain and our prompts), `soapfl_entry.py` (starts SoapFL with
  this chain), `config.py` (builds SoapFL configuration files).
* SoapFL itself is **not modified** for HypoDeduce. The new phases are plugged into the patched SoapFL at start-up,
  so the SoapFL baseline runs exactly as before (`--pipeline soapfl`, the default).

## Paper vs. our implementation

| Step | Paper (Sec. 3) | Our implementation |
|---|---|---|
| Input | failing test(s), as in SoapFL | identical to SoapFL: same failing-test sampling (≤5 test suites, ≤5 tests each), same test-behaviour analysis phase, same covered classes |
| 1. Hypotheses | the LLM proposes several root-cause hypotheses from the test failure | **one** call asks for H different hypotheses, ordered most to least likely (`HypothesisGeneration`, our prompt). One call because SoapFL runs at temperature 0, so repeated samples would be identical. *Ours.* |
| 2. Classes | the C most suspicious covered classes for each hypothesis | one call per hypothesis (`HypothesisClassSearch`, our prompt, modelled on SoapFL's class prompt but asking for C ranked classes). Names outside the covered classes are ignored. |
| 3. Methods | the most relevant methods of those classes for each hypothesis | SoapFL's own related-method prompt, unchanged, asked once per (hypothesis, class), with the hypothesis as the "possible cause". Optional cap per (hypothesis, class) `--hd-methods` (default: no cap, as SoapFL). *Cap is ours.* |
| 4. Retention | an element stays as long as it is consistent with at least one hypothesis | union over hypotheses: a class or method stays if any hypothesis kept it; we record which hypotheses support each method. |
| Method docs | (SoapFL step) | SoapFL's method-summary phase, once per retained class (shared by all hypotheses, so each class is summarised once: the paper's "fetch once and cache"). |
| Scoring | not specified | SoapFL's 1-10 method-review prompt, unchanged, asked once per (method, supporting hypothesis). *Ours.* |
| 5. Selection | evaluate the hypotheses using the accumulated class and method evidence, select the most plausible, which guides the final ranking | plausibility of a hypothesis = best score among the methods it supports, then the mean of its top 3 (`--hd-selection max`, default) or the reverse (`mean_top3`); ties go to the earlier hypothesis. No extra model call. *Ours.* |
| Final ranking | guided by the selected hypothesis | methods supported by the selected hypothesis first, by their score under it; then the other retained methods by their best score under any hypothesis. Equal keys keep review order (stable sort, as SoapFL). Several test suites are merged by keeping each method's best key. *Ours.* |
| Settings | H = C = 5 | defaults H = 5, C = 5; `--hd-hypotheses`, `--hd-classes`. |

Not implemented, because the paper does not describe them: weakening or rejecting hypotheses step by step as
evidence arrives (we evaluate all hypotheses at the end), and any tie-breaking between methods beyond the stable
sort (that is our RQ3, kept separate on purpose).

Sanity check: with H = 1 and C = 1 the pipeline has SoapFL's structure (one hypothesis, one class); the prompts for
the hypothesis and the class differ slightly from SoapFL's, so results are close but not identical.

## Running

Local (Docker + Ollama), from the repo folder:

```powershell
.\run-experiment.cmd qwen25coder -HypoDeduce -N 10      # first 10 bugs: check cost and that it works
.\run-experiment.cmd qwen25coder -HypoDeduce            # the same 100 bugs as the SoapFL baseline
.\run-experiment.cmd qwen25coder -HypoDeduce -H 3 -C 3  # another setting (RQ2 material)
```

CSC: `csc/submit.sh qwen25coder --hypodeduce --n 10` (`--hd-h`, `--hd-c` for other settings).
Manual: `python -m fl_tools run --pipeline hypodeduce --hd-hypotheses 5 --hd-classes 5 --name ... --pilot 10`.

Reports go to `reports/run<N>-<preset>-hd-h<H>c<C>/` with the same files as SoapFL runs (summary, funnel,
ties, per-bug results). Each bug's `result.json` additionally contains a `hypodeduce` block per test suite
(hypotheses, classes and methods per hypothesis, plausibility, selected hypothesis) and, for every ranked
method, its supporting hypotheses and scores. `events.jsonl` has `hd_*` events. The exact prompts used are
saved in the run folder (`_hypodeduce_config/`), and their hash is in `run_meta.json`; a run cannot be resumed
with different H, C or prompts.

## Cost

Model calls per bug grow with H and C: 1 (test behaviour) + 1 (hypotheses) + H (classes) + one summary per
retained class + one method selection per (hypothesis, class) + one review per (method, supporting hypothesis).
With H = C = 5 that is roughly 40-90 calls per bug, against about 10 for SoapFL. Expect a local 100-bug run with
qwen2.5-coder to take several times longer than the SoapFL baseline (about 2 h); measure it on 10 bugs first.
The paper reports +$0.53 and +2.5 min per bug over SoapFL with GPT-4o.

## Tests

`tests/test_hypodeduce_logic.py` (parsing, retention, selection, ranking, configuration, run guard),
`tests/test_hypodeduce_chain.py` (the whole chain inside real SoapFL code against a mock model, incl. resume
from checkpoints and the H = C = 1 case), `tests/test_hypodeduce_runner.py` (runner → SoapFL → result →
score/funnel/ties). Defects4J is faked in these tests; real bugs are only exercised by real runs.
