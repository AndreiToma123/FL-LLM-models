#!/bin/bash
# Template -- fill in the <PLACEHOLDERS> for your CSC project, then: sbatch scripts/slurm_pilot.sbatch
# Check the current partition / GPU names in the CSC docs (docs.csc.fi) before submitting.
#SBATCH --job-name=soapfl-pilot
#SBATCH --account=<YOUR_CSC_PROJECT>
#SBATCH --partition=<GPU_PARTITION>
#SBATCH --gres=gpu:<GPU_TYPE>:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-.}"

# 1) environment (edit configs/example.env first and copy it to configs/local.env)
source configs/local.env
# <load your Java 8 / CUDA / python modules here>

# 2) model server in the background, wait until it answers
bash scripts/serve_vllm.sh "$SOAPFL_MODEL_NAME" 8000 > vllm-$SLURM_JOB_ID.log 2>&1 &
for i in $(seq 1 120); do
  curl -sf "$SOAPFL_BASE_URL/models" >/dev/null && break
  sleep 10
done

# 3) pilot run (resumable: resubmit the job and it continues)
.venv/bin/python -m fl_tools run --name "${RUN_NAME:-pilot-1}" --pilot "${PILOT_N:-30}" --jobs 4 \
  --python .venv/bin/python
.venv/bin/python -m fl_tools score "results/${RUN_NAME:-pilot-1}"
.venv/bin/python -m fl_tools funnel "results/${RUN_NAME:-pilot-1}"
