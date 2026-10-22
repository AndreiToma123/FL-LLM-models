# FL-LLM-models

Reproducing **SoapFL** (LLM-based fault localization, TSE 2025) with an **open-source model**
(Llama / Qwen coder, via Ollama locally or vLLM on a cluster) on **Defects4J**, plus tooling to run it in batches,
score it (Top-1/3/5) and see *where in the pipeline* bugs are lost.

This repository does **not** contain SoapFL's code. It contains a small patch for it, and
the tools around it. `scripts/setup_soapfl.sh` clones SoapFL at a pinned commit and applies the patch.

## Status: what is tested and what is not

| Part | Status |
|---|---|
| Patch applies cleanly to SoapFL `c9f75f4` | verified |
| Patched backend (LOCAL model type) vs. a mock OpenAI server: `<think>` stripping, context budgeting, null content, missing usage, event log | tested (`tests/test_backend.py`) |
| Runner (resume, retries, timeout, run-settings guard), scorer, funnel, bug sampling, preflight | tested with a stub `run.py` and synthetic results |
| Real SoapFL run on real Defects4J bugs with a local model (Docker + Ollama, `qwen2.5-coder:7b`) | worked: 20-bug pilot, results in `reports/pilot-2/` (Top-1/3/5 = 5/8/10 of 20). A 100-bug run is the next baseline. |
| Docker + Ollama setup (`docker/`, `docker-compose.yml`) | used for the pilot, see "Running on your own computer" |
| `scripts/` (cluster: `install_defects4j.sh`, `serve_vllm.sh`, Slurm template) | **untested**; read them, fill in the `<PLACEHOLDERS>` |

`preflight` catches most environment problems cheaply. Results from small samples are exploratory: with 20-100 bugs the
Top-N numbers are only accurate to roughly +-10 points and are not comparable to the paper's 395-bug numbers.

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
(Defects4J does not run natively on Windows). Commands are for PowerShell, run from the repo folder.

### One-time setup (also on a new PC)

1. **Install** Docker Desktop (start it, wait until it says "running") and Ollama. If your C: drive is small, first set
   Docker Desktop's *Settings > Resources > Advanced > Disk image location* and the `OLLAMA_MODELS` environment variable
   to a folder on a bigger drive, *before* downloading models or building.
2. **Have the models** (`ollama list`). The presets in `configs/models.json` need `qwen2.5-coder`, `qwen3.5` and `llama3.1`;
   install a missing one with e.g. `ollama pull qwen2.5-coder`.
3. **Settings:** `copy configs\ollama.env .env`. It only holds the Ollama address. `.env` is git-ignored, so it is **not**
   in the repo and must be recreated on every new machine. The model name and context size are *not* set by hand any more.
4. **Build once** (10-30 minutes, downloads several GB): `docker compose build`

### Running one model, start to finish (one command)

```powershell
.\run-experiment.cmd qwen25coder      # main baseline, 100 bugs
.\run-experiment.cmd llama31          # comparison
.\run-experiment.cmd qwen35 -N 10     # newer Qwen: try 10 bugs first, it may "think" and be slow
```
Add `-Push` to also commit and push the finished `reports/` folder. `-N` sets the number of bugs, `-Jobs` the parallel
bugs (default 2). The `.cmd` file just starts the `.ps1` script with PowerShell's script block lifted, so it works even if PowerShell blocks scripts.

What the command does by itself:
1. Finds the installed Ollama model of that family and **creates a variant with the right context size** (16384) through
   Ollama's API (Ollama otherwise silently cuts long prompts). It is created once and reused.
2. Sets the model name, context limit, token budget and extra settings for this model (`configs/models.json`).
3. Runs the preflight checks (Docker, Defects4J, patch, the model endpoint) and stops with a clear `[FAIL]` line if something is wrong.
4. Runs SoapFL on the same 100 bugs every time (stratified over the six projects), 2 at a time, and keeps the PC awake.
5. Scores the run (Top-1/3/5), runs the funnel analysis, and copies the small result files to `reports\run100-<model>\`
   (read `summary.md` and `funnel.md` there).

* **Resume:** if it stops (sleep, Ctrl+C, crash), run the exact same command again; finished bugs are skipped.
* **The first minutes of every bug show `0 model calls`.** That is normal: SoapFL first checks out, compiles and runs the
  failing test with Defects4J, and only then calls the model.
* **Comparing models:** run the command once per model. Same bugs, same settings except the model, one results folder each.
  Run them whenever you like, they do not have to run back to back.
* **`killed_oom` in the output:** Docker ran out of memory; give Docker more memory or use `-Jobs 1`.
* **Models and presets:** `docker compose run --rm soapfl python -m fl_tools models` shows which presets are available.
  Add your own model by adding an entry to `configs/models.json`.

### Where the data lives
`results/` is a Docker **volume** inside Docker's disk image (Windows shared folders are far too slow for Defects4J builds
and make SoapFL's 90 s test limit fail). It is *not* in your repo folder and *not* on GitHub. Only the export step copies the
small summaries into `reports/`, which you commit and push. The volume and image keep their names (`name: flllmmodels` in
`docker-compose.yml`) even if the folder is moved. Optional backup of the raw runs:
`docker run --rm -v flllmmodels_fl_results:/data -v D:\backup:/backup ubuntu tar czf /backup/fl_results.tgz -C /data .`

### Manual commands (advanced)
```powershell
docker compose run --rm soapfl python -m fl_tools preflight
docker compose run --rm soapfl python -m fl_tools experiment qwen25coder --select Lang-1     # one bug
docker compose run --rm soapfl python -m fl_tools score  results/run100-qwen25coder
docker compose run --rm soapfl python -m fl_tools funnel results/run100-qwen25coder
docker compose run --rm soapfl python -m fl_tools export results/run100-qwen25coder
```
`configs/ollama/Modelfile.*` are the manual way to make a context-size variant; the experiment command does not need them.

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
