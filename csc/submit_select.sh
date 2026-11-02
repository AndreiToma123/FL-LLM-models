#!/usr/bin/env bash
# Submit selector replays (RQ3 judges + offline gate) to CSC Roihu: one GPU runs vLLM as the judge.
# The runs must be in reports/ of this checkout (git pull, or copy them from your PC with scp).
#
#   csc/submit_select.sh <preset> <run>[,<run>...] [options]
#
#   csc/submit_select.sh qwen25coder runall-qwen25coder-csc,runall-qwen25coder-d4j2new-csc
#   csc/submit_select.sh qwen25coder run12-qwen25coder-d4j2new --smoke          (15-min check, 12 bugs)
#   csc/submit_select.sh qwen25coder run100-qwen25coder --split default --reveal-test   (dev/test protocol of 4j)
#   csc/submit_select.sh qwen25coder <hypodeduce run> --shortlist top-k --selector S0,S5,S5+S2,S8a,S8a+S2
#
# Options:
#   --selector LIST   default S0,S0r,S1,S6,S5,S5+S2,S8a,S8a+S2 (the frozen RQ3 set; add S8b for the agent)
#   --ladder LIST     gate ladder scored after the replays (default S6,S8a+S2; 'none' = no gate)
#   --split S         none (default: every bug judged) | default (configs/selection_split.json dev/test) | <file>
#   --reveal-test     with --split default: also judge and report the test part
#   --shortlist M     top-tie (default; SoapFL lists) | top-k (HypoDeduce lists)      --k N (default 8)
#   --out DIR         where the -sel-*/selection/gate reports go (default $FL_ROOT/judge-vllm on scratch: projappl
#                     has a 150k-file quota; a relative DIR is a folder inside the repository)
#   --context         first export the failure context of bugs that have none (runs their failing tests;
#                     needed for new runs whose bugs are not in reports/_failure_context; skipped bugs are free)
#   --jobs N          bugs judged in parallel (default 32)    --time HH:MM:SS (default 04:00:00)
#   --partition P     --name NAME     --smoke (gputest, 15 min)    --dry-run
# Re-submitting the same command resumes: every judge answer is cached in $FL_ROOT/judge-cache/<run>.jsonl.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
cd "$FL_REPO"

die() { echo "ERROR: $*" >&2; exit 1; }
[ $# -ge 2 ] || { sed -n 2,26p "$0"; exit 2; }
PRESET="$1"; RUNS="$2"; shift 2
SELECTORS="S0,S0r,S1,S6,S5,S5+S2,S8a,S8a+S2"; LADDER="S6,S8a+S2"; SPLIT=none; SHORTLIST=top-tie; K=8
OUT=""; CONTEXT=0; SEL_JOBS=32; CTX_JOBS=16; TIME=""; PARTITION=""; NAME=""; SMOKE=0; DRY=0
EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --selector) SELECTORS="$2"; shift ;;
    --ladder) LADDER="$2"; shift ;;
    --split) SPLIT="$2"; shift ;;
    --reveal-test) EXTRA="$EXTRA --reveal-test" ;;
    --shortlist) SHORTLIST="$2"; shift ;;
    --k) K="$2"; shift ;;
    --out) OUT="$2"; shift ;;
    --context) CONTEXT=1 ;;
    --jobs) SEL_JOBS="$2"; shift ;;
    --time) TIME="$2"; shift ;;
    --partition) PARTITION="$2"; shift ;;
    --name) NAME="$2"; shift ;;
    --smoke) SMOKE=1 ;;
    --dry-run) DRY=1 ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

case "$SHORTLIST" in top-tie|top-k) ;; *) die "unknown --shortlist $SHORTLIST (top-tie or top-k)" ;; esac
case "$SPLIT" in
  none) ;;
  default) SPLIT=configs/selection_split.json ;;
  *) [ -f "$SPLIT" ] || die "split file $SPLIT not found" ;;
esac
[ "$LADDER" = none ] && LADDER=""
if [ -z "$OUT" ]; then if [ "$SMOKE" = 1 ]; then OUT="$FL_ROOT/judge-vllm-smoke"; else OUT="$FL_ROOT/judge-vllm"; fi; fi
if [ -n "$LADDER" ]; then           # the gate reads the replays of its ladder: they must be in this job (or done earlier)
  IFS=',' read -r -a L <<< "$LADDER"
  for s in "${L[@]}"; do
    [[ ",$SELECTORS," == *",$s,"* ]] || [ -d "$OUT" ] || die "ladder step $s is not in --selector $SELECTORS"
  done
fi

IFS=',' read -r -a RUN_LIST <<< "$RUNS"
for r in "${RUN_LIST[@]}"; do
  [ -f "reports/$r/runs.jsonl" ] || die "reports/$r not found here ($FL_REPO); git pull, or scp it from your PC"
done

# preset -> judge model (configs/models.json, the same model that produced the candidate lists)
eval "$(python3 - "$FL_REPO/configs/models.json" "$PRESET" <<'PY'
import json, shlex, sys
presets = json.load(open(sys.argv[1]))
name = sys.argv[2]
p = presets.get(name)
if p is None or name.startswith("_") or not p.get("hf"):
    print(f"echo 'unknown preset {name} (or no hf repo in configs/models.json)' >&2; exit 2"); sys.exit()
print(f"HF_REPO={shlex.quote(p['hf'])}")
print(f"CTX={shlex.quote(str(p.get('num_ctx', 16384)))}")
PY
)"
MODEL_DIR="$MODELS_DIR/$(echo "$HF_REPO" | tr '/' '_')"
[ -f "$SOAPFL_SIF" ] || die "image $SOAPFL_SIF missing: run csc/setup.sh image (on roihu-gpu.csc.fi)"
ls "$MODEL_DIR"/*.safetensors >/dev/null 2>&1 || die "weights of $HF_REPO missing: run csc/setup.sh model $PRESET"

if [ "$SMOKE" = 1 ]; then
  PARTITION="${PARTITION:-gputest}"; TIME="${TIME:-00:15:00}"; ENFORCE_EAGER=1
  NAME="${NAME:-select-smoke}"
else
  PARTITION="${PARTITION:-gpumedium}"; TIME="${TIME:-04:00:00}"; ENFORCE_EAGER=0
  NAME="${NAME:-select-${RUN_LIST[0]}$( [ "${#RUN_LIST[@]}" -gt 1 ] && echo "-and-$(( ${#RUN_LIST[@]} - 1 ))" || true )}"
fi

mkdir -p "$FL_ROOT/logs"
JOB_ENV="$FL_ROOT/logs/$NAME-$(date +%Y%m%d-%H%M%S).env"
{
  for v in PRESET:FL_PRESET RUNS:FL_RUNS SELECTORS:FL_SELECTORS LADDER:FL_LADDER SPLIT:FL_SPLIT \
           SHORTLIST:FL_SHORTLIST K:FL_K OUT:FL_OUT CONTEXT:FL_CONTEXT SEL_JOBS:FL_SEL_JOBS CTX_JOBS:FL_CTX_JOBS \
           EXTRA:FL_EXTRA HF_REPO:FL_HF_REPO MODEL_DIR:FL_MODEL_DIR CTX:FL_CTX ENFORCE_EAGER:FL_ENFORCE_EAGER \
           FL_REPO:FL_REPO; do
    src="${v%%:*}"; printf '%s=%q\n' "${v#*:}" "${!src}"
  done
} > "$JOB_ENV"
CMD=(sbatch --account="$CSC_PROJECT" --partition="$PARTITION" --time="$TIME" --gres="$GPU_GRES"
     --job-name="fl-$NAME" --output="$FL_ROOT/logs/%x-%j.out"
     --export=ALL,FL_JOB_ENV="$JOB_ENV" "$FL_REPO/csc/select_job.sbatch")
echo "select job $NAME: judge $PRESET ($HF_REPO) on ${#RUN_LIST[@]} run(s): $RUNS"
echo "  selectors $SELECTORS; gate ${LADDER:-none}; split $SPLIT; shortlist $SHORTLIST; out $OUT; partition $PARTITION, limit $TIME"
if [ "$DRY" = 1 ]; then printf '%q ' "${CMD[@]}"; echo; exit 0; fi
"${CMD[@]}"
echo "follow it with:  squeue --me    and    tail -f $FL_ROOT/logs/fl-$NAME-<jobid>.out"
