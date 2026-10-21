# FL-LLM-models

Reproducing **SoapFL** (LLM-based fault localization, TSE 2025) with an **open-source model**
(Llama 3 / Qwen coder served by vLLM) on **Defects4J**, plus tooling to run it in batches,
score it (Top-1/3/5) and see *where in the pipeline* bugs are lost.

This repository does **not** contain SoapFL's code. It contains a small patch for it, and
the tools around it. `scripts/setup_soapfl.sh` clones SoapFL at a pinned commit and applies the patch.

## Status: what is tested and what is not

| Part | Status |
|---|---|
| Patch applies cleanly to SoapFL `c9f75f4` | verified |
| Patched backend (LOCAL model type) vs. a mock OpenAI server: `<think>` stripping, context budgeting, null content, missing usage, event log | tested (`tests/test_backend.py`) |
| Runner (resume, retries, timeout, run-settings guard), scorer, funnel, bug sampling, preflight | tested with a stub `run.py` and synthetic results |
| **A real SoapFL run on real Defects4J bugs with a real GPU model** | **NOT done yet. It was not possible where this code was written.** |
| `scripts/install_defects4j.sh`, `scripts/serve_vllm.sh`, Slurm template | **untested**; read them, fill in the `<PLACEHOLDERS>` |

So expect to fix small environment problems on the first real run. `preflight` exists to catch most of them cheaply.

## Quick start (CSC or any Linux box with a GPU)

```bash
bash scripts/setup_soapfl.sh              # clone SoapFL, apply patch, make .venv, warm tiktoken cache
bash scripts/install_defects4j.sh         # Java 8 required; see the script first
cp configs/example.env configs/local.env  # edit model name, context length, paths
source configs/local.env

bash scripts/serve_vllm.sh                # in another shell / background: serves the model
.venv/bin/python -m fl_tools preflight    # must show 0 failures
```

Then, smallest to largest:

```bash
# 1. one bug, to see that everything works end to end
.venv/bin/python -m fl_tools run --name smoke --bugs Lang-1 --python .venv/bin/python
# 2. pilot: 30 bugs sampled over all six projects (deterministic)
.venv/bin/python -m fl_tools run --name pilot-1 --pilot 30 --jobs 4 --python .venv/bin/python
# 3. results
.venv/bin/python -m fl_tools score  results/pilot-1
.venv/bin/python -m fl_tools funnel results/pilot-1
```

Runs are **resumable**: run the same command again and finished bugs are skipped.
On CSC use `scripts/slurm_pilot.sbatch` (placeholders for project, partition and GPU).

## Running on your own computer (Ollama + Docker)

No cluster needed. Ollama runs the model on your machine (it uses your GPU); Docker runs SoapFL, Java 8 and Defects4J
(Defects4J does not run natively on Windows). **Untested end to end** -- I had no Docker or Ollama where this was written.

1. **Model with a large enough context.** Ollama's default context is only a few thousand tokens and it *silently cuts*
   longer prompts, which would quietly ruin SoapFL (its prompts are long). Create a variant (check your tag with `ollama list`):
   ```powershell
   ollama create soapfl-qwen -f configs/ollama/Modelfile.qwen     # edit the FROM tag first
   ```
   Context costs memory (16k is fine for a 7-8B model on most 16 GB GPUs/RAM; lower `num_ctx` if it is too slow or out of memory).
2. **Settings:** `copy configs\ollama.env .env` and edit (model name, and `SOAPFL_CONTEXT_LIMIT` <= `num_ctx`).
3. **Build once** (long: Defects4J downloads several GB): `docker compose build`
4. **Check:** `docker compose run --rm soapfl python -m fl_tools preflight` -- it also reads the model's `num_ctx` from Ollama and fails if it is too small.
5. **Run:**
   ```powershell
   docker compose run --rm soapfl python -m fl_tools run --name smoke --bugs Lang-1
   docker compose run --rm soapfl python -m fl_tools run --name pilot-1 --pilot 20
   docker compose run --rm soapfl python -m fl_tools score results/pilot-1
   docker compose run --rm soapfl python -m fl_tools funnel results/pilot-1
   ```
   Keep `--jobs 1` (the default): one local model serves one request at a time, more jobs just queue and use more memory.
   Expect each bug to take many minutes on a local 7-8B model. Results live in a Docker volume (Windows shared folders are too slow for Defects4J builds and make SoapFL's 90 s test
   limit fail). Copy the small summary files into your repo folder with
   `docker compose run --rm soapfl python -m fl_tools export results/pilot-1` (they appear in `reports/pilot-1/`).
   The first minutes of every bug show `0 model calls`: SoapFL first checks out, compiles and runs the failing test
   with Defects4J, and only then calls the model.

## Rules that protect your results

* **One run name per model/config.** SoapFL caches every LLM answer inside the output folder and reuses it silently.
  The runner writes `run_meta.json` and refuses to resume a folder if the model, context limit, parsing mode or seed changed.
* **Lenient vs strict parsing.** Original SoapFL crashes a bug when the model does not output a score as `#N#`.
  Default here is *lenient*: it accepts a few common variants, otherwise scores the method 0 and records a `score_unparsed` event
  (so format failures of small models become measurable data). `--strict` restores the original behaviour.
* A bug counts as finished only if `result.json` exists. Bugs without output count as **not localized**
  in the denominator (as in SoapFL's own evaluation).
* Seeds: `--seed` sets `SOAPFL_SEED` (per-bug test sampling) and the runner sets `PYTHONHASHSEED=0`.
  GPU sampling can still differ between runs; the SoapFL pipeline uses temperature settings from its own config.

## What the outputs mean

`results/<name>/`
* `summary.md` / `summary.json`: Top-1/3/5 per project and overall, tokens per bug. The SoapFL paper's GPT-3.5 numbers
  (175/232/236 of 395) are printed as a *rough* reference. Compare percentages only, and only on large samples.
* `per_bug.csv`, `per_bug_soapfl_format.csv` (the 10-column format SoapFL's own `Evaluation/` scripts read).
* `funnel.md`: how many bugs survive each stage (output produced → right class → buggy method reached ranking → top 5 → top 1),
  why the rest were lost (crash, no valid class, context overflow, class missed, ...), and how many Top-1 hits are
  *ties* decided only by review order. This mirrors the funnel analysis in the HypoDeduce paper.
* `events.jsonl` (inside each bug folder): every LLM call (latency, tokens, finish reason) and every parse/overflow incident.

`python -m fl_tools score RUN --reference-csv some_soapfl_results.csv` compares bug by bug with another run in SoapFL's CSV format.

## Known differences from the paper

* The batch list has **388** bugs (SoapFL's `run_all.py` skips 7 deprecated IDs); the paper's Table I says 395.
  Use `--include-deprecated` to select all 395 IDs.
* Defects4J 1.4.0 is used (same bugs as 1.2.0 per the SoapFL README).
* Open models are weaker at following SoapFL's rigid output formats. Expect a lower score and more crashes; the point of
  this repo is to measure that, not hide it. Full list of code changes: `docs/PATCH_NOTES.md`.

## Tests

```bash
.venv/bin/python -m pytest                        # fast tests (no SoapFL needed)
SOAPFL_DIR=external/SoapFL .venv/bin/python -m pytest   # also backend tests (default path used if present)
```

## Scope

This is about *localizing bugs that are already known and fixed* in a benchmark (defensive software-quality research).
It does not generate exploits or attack code.
