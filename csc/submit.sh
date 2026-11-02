#!/usr/bin/env bash
# Submit one SoapFL experiment to CSC Roihu: one GPU (vLLM) + many SoapFL workers on the same node.
#
#   csc/submit.sh <preset> --smoke            1 bug on the 15-min test partition (check the setup works)
#   csc/submit.sh <preset> --n 10             10 bugs (same stratified sample as locally)
#   csc/submit.sh <preset>                    100 bugs (default)
#   csc/submit.sh <preset> --select Lang-1,Math-3
#   csc/submit.sh <preset> --hypodeduce --n 10 [--hd-h 5 --hd-c 5 --hd-m 3]   our HypoDeduce re-implementation
#   add --subset-of 100 to take the --n bugs from the 100 baseline bugs
#   csc/submit.sh <preset> --n all                        all 388 bugs of Defects4J 1.4.0 (dataset 1)
#   csc/submit.sh <preset> --dataset d4j2new --n all      all 444 bugs Defects4J 2.0 added (dataset 2)
#   csc/submit.sh <preset> --classaug [--ca-k 3] [--ca-mode always|gated] --n all
#                                             SoapFL + free class ranking (RQ1: always, RQ2: gated)
# Options: --name RUN (default run<N>-<preset>-csc)  --jobs N (default: automatic)  --time HH:MM:SS
#          --partition P  --seed S  --dry-run (print the sbatch command only)
#
# Billing: 200 GPU billing units per GPU-hour of the job's ELAPSED time (not of --time). Re-submitting the
# same command resumes a run: finished bugs are skipped.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
cd "$FL_REPO"

die() { echo "ERROR: $*" >&2; exit 1; }
[ $# -ge 1 ] || { sed -n 2,12p "$0"; exit 2; }
PRESET="$1"; shift
N=100; SELECT=""; NAME=""; JOBS="auto"; TIME=""; PARTITION=""; SEED=0; SMOKE=0; DRY=0
PIPELINE=soapfl; HD_H=5; HD_C=5; HD_M=0; SUBSET_OF=0; DATASET=d4j14; CA_K=3; CA_MODE=always
while [ $# -gt 0 ]; do
  case "$1" in
    --smoke) SMOKE=1 ;;
    --n) N="$2"; shift ;;
    --select) SELECT="$2"; shift ;;
    --name) NAME="$2"; shift ;;
    --jobs) JOBS="$2"; shift ;;
    --time) TIME="$2"; shift ;;
    --partition) PARTITION="$2"; shift ;;
    --seed) SEED="$2"; shift ;;
    --dry-run) DRY=1 ;;
    --hypodeduce) PIPELINE=hypodeduce ;;
    --hd-h) HD_H="$2"; shift ;;
    --hd-c) HD_C="$2"; shift ;;
    --hd-m) HD_M="$2"; shift ;;
    --subset-of) SUBSET_OF="$2"; shift ;;
    --dataset) DATASET="$2"; shift ;;
    --classaug) PIPELINE=classaug ;;
    --ca-k) CA_K="$2"; shift ;;
    --ca-mode) CA_MODE="$2"; shift ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

# preset -> model settings (configs/models.json, shared with the local pipeline)
eval "$(python3 - "$FL_REPO/configs/models.json" "$PRESET" <<'PY'
import json, shlex, sys
presets = json.load(open(sys.argv[1]))
name = sys.argv[2]
p = presets.get(name)
if p is None or name.startswith("_"):
    print(f"echo 'unknown preset {name}; known: {', '.join(k for k in presets if not k.startswith('_'))}' >&2; exit 2"); sys.exit()
if not p.get("hf"):
    print(f"echo 'preset {name} has no hf repo in configs/models.json, so it cannot run on CSC' >&2; exit 2"); sys.exit()
out = {"HF_REPO": p["hf"], "CTX": p.get("num_ctx", 16384), "MAX_TOKENS": p.get("max_completion_tokens", 3072),
       "EXTRA_BODY": json.dumps(p.get("extra_body") or {})}
for k, v in out.items():
    print(f"{k}={shlex.quote(str(v))}")
PY
)"

MODEL_DIR="$MODELS_DIR/$(echo "$HF_REPO" | tr '/' '_')"
[ -f "$SOAPFL_SIF" ] || die "image $SOAPFL_SIF missing: run csc/setup.sh image (on roihu-gpu.csc.fi)"
ls "$MODEL_DIR"/*.safetensors >/dev/null 2>&1 || die "weights of $HF_REPO missing: run csc/setup.sh model $PRESET"

PIPELINE_ARGS=""; SUFFIX=""
if [ "$PIPELINE" = hypodeduce ]; then
  # 1 h per bug: on CSC the slowest finished HypoDeduce bug took 16 min (2026-11-01); 3 h only held the GPU for a hung bug
  PIPELINE_ARGS="--pipeline hypodeduce --hd-hypotheses $HD_H --hd-classes $HD_C --hd-methods $HD_M --timeout 3600"
  SUFFIX="-hd-h${HD_H}c${HD_C}"
  [ "$HD_M" != 0 ] && SUFFIX="${SUFFIX}m${HD_M}"
fi
if [ "$PIPELINE" = classaug ]; then
  case "$CA_MODE" in always|gated) ;; *) die "unknown --ca-mode $CA_MODE (always or gated)" ;; esac
  [ -d "$FL_REPO/reports/_failure_context" ] || die "reports/_failure_context missing: git pull (it is in the repository)"
  PIPELINE_ARGS="--pipeline classaug --ca-k $CA_K --ca-mode $CA_MODE"
  # (not `$( [ ... ] && echo g )`: under `set -e` its false test ends the script silently in `always` mode)
  SUFFIX="-ca${CA_K}"
  if [ "$CA_MODE" = gated ]; then SUFFIX="${SUFFIX}g"; fi
fi
case "$DATASET" in d4j14|d4j2new) ;; *) die "unknown dataset $DATASET (d4j14 or d4j2new)" ;; esac
if [ "$DATASET" != d4j14 ]; then
  PIPELINE_ARGS="$PIPELINE_ARGS --dataset $DATASET"
  SUFFIX="${SUFFIX}-$DATASET"
fi
SIZE="$N"
if [ "$SUBSET_OF" != 0 ] && [ "$SUBSET_OF" -gt "$N" ]; then
  PIPELINE_ARGS="$PIPELINE_ARGS --subset-of $SUBSET_OF"
  SIZE="${N}of${SUBSET_OF}"
fi

if [ "$SMOKE" = 1 ]; then
  if [ "$DATASET" = d4j14 ]; then SELECT="${SELECT:-Lang-1}"; else SELECT="${SELECT:-Cli-1}"; fi
  NAME="${NAME:-smoke-$PRESET$SUFFIX-csc}"
  PARTITION="${PARTITION:-gputest}"
  TIME="${TIME:-00:15:00}"
  ENFORCE_EAGER=1          # skip CUDA-graph capture: faster start, enough for one bug
else
  if [ -n "$SELECT" ]; then
    NAME="${NAME:-sel-$PRESET$SUFFIX-csc}"
  else
    NAME="${NAME:-run$SIZE-$PRESET$SUFFIX-csc}"
  fi
  PARTITION="${PARTITION:-gpumedium}"
  # generous limit: billing counts elapsed time only; the job stops itself when the bugs are done
  TIME="${TIME:-04:00:00}"
  ENFORCE_EAGER=0
fi

mkdir -p "$FL_ROOT/logs"
# job settings go through a file: sbatch --export cannot carry values with commas (bug lists, JSON)
JOB_ENV="$FL_ROOT/logs/$NAME-$(date +%Y%m%d-%H%M%S).env"
{
  for v in PRESET:FL_PRESET NAME:FL_RUN N:FL_N SELECT:FL_SELECT JOBS:FL_JOBS SEED:FL_SEED HF_REPO:FL_HF_REPO \
           MODEL_DIR:FL_MODEL_DIR CTX:FL_CTX MAX_TOKENS:FL_MAX_TOKENS EXTRA_BODY:FL_EXTRA_BODY \
           ENFORCE_EAGER:FL_ENFORCE_EAGER FL_REPO:FL_REPO PIPELINE_ARGS:FL_PIPELINE_ARGS DATASET:FL_DATASET; do
    src="${v%%:*}"; printf '%s=%q\n' "${v#*:}" "${!src}"
  done
} > "$JOB_ENV"
CMD=(sbatch --account="$CSC_PROJECT" --partition="$PARTITION" --time="$TIME" --gres="$GPU_GRES"
     --job-name="fl-$NAME" --output="$FL_ROOT/logs/%x-%j.out"
     --export=ALL,FL_JOB_ENV="$JOB_ENV" "$FL_REPO/csc/run_job.sbatch")
echo "run $NAME: preset $PRESET ($HF_REPO), $( [ -n "$SELECT" ] && echo "bugs $SELECT" || echo "$N bugs" ), partition $PARTITION, limit $TIME"
if [ "$DRY" = 1 ]; then printf '%q ' "${CMD[@]}"; echo; exit 0; fi
"${CMD[@]}"
echo "follow it with:  squeue --me    and    tail -f $FL_ROOT/logs/fl-$NAME-<jobid>.out"
