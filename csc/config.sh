# shellcheck shell=bash
# Settings shared by the CSC (Roihu) scripts. Sourced, not executed.
# Override any value by exporting it before calling a script, e.g.  FL_ROOT=/scratch/... csc/submit.sh ...

CSC_PROJECT="${CSC_PROJECT:-project_2021789}"

# Repository (this checkout). Keep it in projappl (persistent, 15 GiB) or home.
FL_REPO="${FL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Big and many-file data: container image, model weights, results. Scratch has 250 GiB / 500k files.
# Roihu's exact scratch path is not confirmed in the docs we read; `csc-workspaces` shows it.
FL_ROOT="${FL_ROOT:-/scratch/${CSC_PROJECT}/${USER}/fl}"

SOAPFL_SIF="${SOAPFL_SIF:-$FL_ROOT/images/soapfl-aarch64.sif}"   # our SoapFL+Defects4J image (GPU nodes are ARM)
MODELS_DIR="${MODELS_DIR:-$FL_ROOT/models}"                       # one folder per Hugging Face repo
RESULTS_DIR="${RESULTS_DIR:-$FL_ROOT/results}"                    # persistent copy of every run (resume source)
SOAPFL_CACHE="${SOAPFL_CACHE:-$FL_ROOT/soapfl-cache}"             # SoapFL's per-bug failing-test cache, reused across runs
HF_HOME="${HF_HOME:-$FL_ROOT/hf-cache}"

# vLLM comes from CSC's module (it brings its own container, $SIF). Pin the version for reproducibility.
VLLM_MODULE="${VLLM_MODULE:-python-vllm/0.29.0}"

# Slurm defaults (GPU partitions per docs.csc.fi, read 2026-10-22: gputest 15 min, gpumedium up to 36 h).
GPU_GRES="${GPU_GRES:-gpu:gh200:1}"

# Parallel SoapFL workers on one GPU node share 72 cores and ~117 GiB of host memory with vLLM.
# Per worker we budget 3 cores and 4 GiB (a Defects4J compile + test run), and keep 8 cores / 24 GiB for vLLM.
CORES_PER_WORKER="${CORES_PER_WORKER:-3}"
MEM_GIB_PER_WORKER="${MEM_GIB_PER_WORKER:-4}"
RESERVED_CORES="${RESERVED_CORES:-8}"
RESERVED_MEM_GIB="${RESERVED_MEM_GIB:-24}"
HOST_MEM_GIB="${HOST_MEM_GIB:-117}"     # LPDDR5 per GPU on GH200 (the other 95 GiB of the 212 GiB is GPU HBM)
MAX_WORKERS="${MAX_WORKERS:-24}"

export CSC_PROJECT FL_REPO FL_ROOT SOAPFL_SIF MODELS_DIR RESULTS_DIR SOAPFL_CACHE HF_HOME VLLM_MODULE GPU_GRES
export CORES_PER_WORKER MEM_GIB_PER_WORKER RESERVED_CORES RESERVED_MEM_GIB HOST_MEM_GIB MAX_WORKERS
