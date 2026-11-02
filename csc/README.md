# CSC pipeline (Roihu)

The **local pipeline** (Docker + Ollama, `run-experiment.cmd`) stays the default for most experiments.
This folder is the **CSC pipeline** for runs that need a bigger GPU or must be fast. Both pipelines use the
same code (`fl_tools/`), the same SoapFL patch and the same model presets (`configs/models.json`).

Project `project_2021789` has about **50 GPU-hours** (10,000 GPU billing units at 200 BU per GPU-hour).
You pay for the elapsed time of a job, not for the `--time` you ask for, so the scripts finish as soon
as the bugs are done.

## How one job works

One job reserves **one GH200 GPU** on `gpumedium` (72 CPU cores and about 117 GiB of host memory come with
it at no extra cost). Inside the job:

1. vLLM (CSC's `python-vllm` module) loads the model and listens on a Unix socket, as in CSC's own examples
   (a socket file instead of a network port, so other users on the node cannot reach it).
2. SoapFL runs in our Apptainer image (`soapfl-aarch64.sif`: Java 8, Defects4J 1.4.0, SoapFL + patch)
   with many bugs in parallel. The number of workers is computed from the node: 3 cores and 4 GiB per
   worker, 8 cores and 24 GiB kept for vLLM, at most 24 (all in `csc/config.sh`).
3. Bugs run on the node's local disk (`$TMPDIR`), which is fast and does not count against the scratch
   file quota. Every 5 minutes, and at the end, results are copied to scratch.
4. At the end: score, funnel, tie analysis and export to `reports/<run>/` in the repository.
   `job_meta.json` records the node, GPU, vLLM version, workers, timing and the estimated GPU billing units.

If the time limit comes close, the job stops the workers and saves progress. Submitting the same command
again resumes the run: finished bugs are skipped.

## One-time setup (on the GPU login node)

```bash
ssh andreist@roihu-gpu.csc.fi        # GPU nodes are ARM: build on the ARM login node
cd /projappl/project_2021789          # or wherever `csc-workspaces` shows your projappl
git clone https://github.com/AndreiToma123/FL-LLM-models.git && cd FL-LLM-models
csc/setup.sh check                    # shows what exists; prints csc-workspaces
csc/setup.sh dirs
csc/setup.sh image                    # 30-60 min, downloads several GB; login nodes cost nothing
csc/setup.sh model qwen25coder        # ~15 GB of weights into scratch
csc/setup.sh check
```

If `csc/setup.sh dirs` says the scratch path does not exist, run `csc-workspaces` and set
`export FL_ROOT=/your/scratch/path/$USER/fl` before the other commands (put it in `~/.bashrc`).

Gated models (Llama): accept the license on huggingface.co, create a read token, then
`export HF_TOKEN=...` before `csc/setup.sh model llama31`.

## Running

```bash
csc/submit.sh qwen25coder --smoke     # 1 bug (Lang-1) on gputest, at most 15 min: does everything work?
csc/submit.sh qwen25coder --n 10      # 10 bugs (same stratified sample as locally)
csc/submit.sh qwen25coder             # 100 bugs
csc/submit.sh qwen25coder32           # the 32B coder model (download it first)
csc/submit.sh qwen25coder --n all                          # all 388 Defects4J 1.4.0 bugs (dataset 1)
csc/submit.sh qwen25coder --smoke --dataset d4j2new        # 1 bug (Cli-1) of dataset 2
csc/submit.sh qwen25coder --dataset d4j2new --n all        # all 444 bugs Defects4J 2.0 added (dataset 2)
squeue --me                           # is it running?
tail -f /scratch/project_2021789/$USER/fl/logs/fl-<run>-<jobid>.out
```

Run names end in `-csc` (e.g. `run100-qwen25coder-csc`) so they never mix with local runs.
Reports land in `reports/<run>/` of the clone on Roihu. Get them to your PC with
`scp -r andreist@roihu-gpu.csc.fi:/projappl/project_2021789/FL-LLM-models/reports/<run> reports/`
or commit and push from Roihu.

## Selector replays (RQ3 judge) on CSC

The selectors (S0 ... S8a+S2, S8b) and the offline gate only re-read the candidate lists of a finished run in
`reports/<run>/`; on CSC the judge is served by vLLM (same bf16 model as the SoapFL runs), not Ollama.

```bash
bash csc/submit_select.sh qwen25coder run12-qwen25coder-d4j2new --smoke                 # 15-min check
bash csc/submit_select.sh qwen25coder runall-qwen25coder-csc,runall-qwen25coder-ca3-csc  # several runs, one job
bash csc/submit_select.sh qwen25coder <hypodeduce run> --shortlist top-k                 # HypoDeduce lists
bash csc/submit_select.sh qwen25coder run100-qwen25coder --split default --reveal-test   # dev/test protocol
```

- Default selectors = the frozen RQ3 set `S0,S0r,S1,S6,S5,S5+S2,S8a,S8a+S2`; default gate ladder `S6,S8a+S2`.
- Reports go to `$FL_ROOT/judge-vllm/` on scratch (projappl has a 150k-file quota; `--out reports/x` writes into the repo instead) (`<run>-sel-*`, `<run>-selection.md`, `<run>-gate.md`,
  `<run>-judge-job.json` with elapsed time and GPU BU), so the Ollama-judge reports next to the runs stay.
- Judge answers are cached per run in `$FL_ROOT/judge-cache/<run>.jsonl`: re-submitting the same command after a
  time limit continues where it stopped.
- `--context` first exports the failure context of bugs missing in `reports/_failure_context` (runs their failing
  tests; all 832 dataset-1/2 bugs already have one, so only needed for other bugs).
- vLLM gets `--enable-auto-tool-choice --tool-call-parser hermes` for the agent selector S8b (native tool calls).

## Spending the GPU budget carefully

- Debug locally first. Use `--smoke` (15 min max) before any larger CSC run.
- Keep `--jobs auto`: fewer workers leave the GPU idle while Defects4J compiles and tests.
- Check `job_meta.json` after each run (`gpu_billing_units_est`) and `csc-projects` / MyCSC for the balance.
- Rough expectation, NOT measured yet: a 100-bug run with a 7B model about 0.5-2 GPU-hours.

## Not verified yet (the smoke test will tell)

- Roihu's scratch path (`/scratch/project_2021789` assumed) and that `csc-common-bind` exists as in CSC's examples.
- Building the image with `--fakeroot` on Roihu (Ubuntu base on a Rocky host). Fallback: build the image
  on your PC with Docker for `linux/arm64` (`docker buildx build --platform linux/arm64 -f docker/Dockerfile -t soapfl-arm64 --load .`,
  then `docker save soapfl-arm64 -o soapfl-arm64.tar`), copy the tar to scratch and run
  `apptainer build soapfl-aarch64.sif docker-archive://soapfl-arm64.tar`. The Dockerfile then needs
  `JAVA_HOME=/usr/lib/jvm/java-8-openjdk-arm64`.
- That all Python dependencies install on ARM (`tree_sitter<0.22` may compile from source).
- vLLM flags (`--uds`, `--max-num-seqs`) for the module version in `csc/config.sh`.
- Whether compute nodes have internet. The scripts do not need it (`HF_HUB_OFFLINE=1`).

## Differences to the local pipeline (matter when comparing results)

- Local Ollama tags are 4-bit quantized (`qwen2.5-coder:latest` is 7B Q4); CSC serves the original
  bf16 weights from Hugging Face. Same preset, slightly different model.
- Different server (vLLM vs Ollama): sampling defaults and tokenizer templates can differ.
- SoapFL's failing-test cache is reused across CSC runs (it does not depend on the model); locally each
  Docker run rebuilds it.
