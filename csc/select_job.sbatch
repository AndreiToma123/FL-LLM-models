#!/bin/bash
# One CSC Roihu job = one GPU running vLLM as the JUDGE + the selector replays (RQ3) of one or more finished runs.
# No SoapFL, no Defects4J: the selectors only re-read the candidate lists saved in reports/<run>/ and ask the judge.
# (Exception: bugs without a failure-context file are exported first, which runs their failing tests; normally 0.)
# Submit it with csc/submit_select.sh (which sets account, partition, time and the job settings file).
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=72
#SBATCH --mem=217000M
#SBATCH --signal=B:USR1@300
set -uo pipefail

: "${FL_JOB_ENV:?submit this job with csc/submit_select.sh}"
source "$FL_JOB_ENV"
source "$FL_REPO/csc/config.sh"

T0=$(date +%s)
log() { echo "[$(date +%H:%M:%S)] $*"; }
fail() { log "FAILED: $*"; exit 1; }

WORK="${TMPDIR:?}/fl-sel-$SLURM_JOB_ID"           # node-local scratch (context export checkouts), deleted after the job
JUDGE_CACHE_DIR="$FL_ROOT/judge-cache"            # judge answers, persistent: a re-submitted job repeats no call
# Reports go to scratch by default (projappl has a 150k-file quota; one full replay writes ~13k files).
# An absolute --out is bound into the container as /work/out; a relative one is a folder inside the repository.
case "$FL_OUT" in
  /*) OUT_DIR="$FL_OUT"; OUT_C=/work/out ;;
  *)  OUT_DIR="$FL_REPO/$FL_OUT"; OUT_C="/work/repo/$FL_OUT" ;;
esac
mkdir -p "$WORK/results/_failure_context" "$WORK/cache" "$JUDGE_CACHE_DIR" "$OUT_DIR" "$FL_ROOT/logs" \
  || fail "cannot create folders"
log "job $SLURM_JOB_ID on $(hostname): judge $FL_PRESET ($FL_HF_REPO); runs: $FL_RUNS"
log "selectors $FL_SELECTORS; ladder ${FL_LADDER:-none}; split $FL_SPLIT; shortlist $FL_SHORTLIST (K $FL_K); out $FL_OUT; judge question limit ${FL_CALL_TIMEOUT:-120}s"

IFS=',' read -r -a RUNS <<< "$FL_RUNS"
for r in "${RUNS[@]}"; do
  [ -f "$FL_REPO/reports/$r/runs.jsonl" ] || [ -d "$FL_REPO/reports/$r/bugs" ] \
    || fail "reports/$r not found in $FL_REPO (git pull, or copy the run folder here)"
done

# ---------------------------------------------------------------- container (fl_tools + SoapFL helpers)
{
  printf 'SOAPFL_UDS=%q\n' "${TMPDIR}/vllm-$SLURM_JOB_ID.sock"
  printf 'SOAPFL_BASE_URL=%q\n' "http://localhost/v1"
  printf 'SOAPFL_API_KEY=%q\n' "EMPTY"
  printf 'TMPDIR=%q\n' "$TMPDIR"
} > "$WORK/fl.env"
SF=(apptainer exec --cleanenv --writable-tmpfs --env-file "$WORK/fl.env"
    --bind="$(csc-common-bind)" --bind="$TMPDIR" --bind="$WORK/cache:/opt/SoapFL/cache"
    --bind="$JUDGE_CACHE_DIR:/work/judge" --bind="$FL_REPO:/work/repo" --bind="$OUT_DIR:/work/out" --pwd /work/repo "$SOAPFL_SIF")

# ---------------------------------------------------------------- failure context for bugs that have none
# Already exported bugs are copied in first, so the exporter skips them (it is resumable per file).
cp -n "$FL_REPO"/reports/_failure_context/*.json "$WORK/results/_failure_context/" 2>/dev/null
if [ "$FL_CONTEXT" = 1 ]; then
  CTX_ARGS=()
  for r in "${RUNS[@]}"; do CTX_ARGS+=("reports/$r"); done
  log "failure context: exporting missing bugs (CPU, Defects4J), $FL_CTX_JOBS in parallel"
  "${SF[@]}" python -m fl_tools context "${CTX_ARGS[@]}" --jobs "$FL_CTX_JOBS" \
    --results-dir "$WORK/results" --reports-dir /work/repo/reports 2>&1 | tail -20
fi

# ---------------------------------------------------------------- vLLM judge server
module purge
module load "$VLLM_MODULE" || fail "module $VLLM_MODULE not available (module spider python-vllm)"
SOCK="$TMPDIR/vllm-$SLURM_JOB_ID.sock"
if [ "${#SOCK}" -gt 100 ]; then
  SOCK_DIR="/tmp/fl-$USER-$SLURM_JOB_ID"; mkdir -p "$SOCK_DIR"; chmod 700 "$SOCK_DIR"; SOCK="$SOCK_DIR/vllm.sock"
  sed -i "s|^SOAPFL_UDS=.*|SOAPFL_UDS=$SOCK|" "$WORK/fl.env"
fi
export HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCHINDUCTOR_CACHE_DIR="$TMPDIR/torch-cache"
# Same serving settings as the SoapFL jobs (run_job.sbatch), plus a tool-call parser for the agent selector S8b
# (hermes = the parser vLLM documents for Qwen2.5). max-logprobs 20 = what S2 asks for (top_logprobs 20).
VLLM_ARGS=(serve "$FL_MODEL_DIR" --served-model-name "$FL_PRESET" --uds "$SOCK"
           --max-model-len "$FL_CTX" --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0
           --max-logprobs 20 --enable-auto-tool-choice --tool-call-parser hermes)
[ "${FL_ENFORCE_EAGER:-0}" = 1 ] && VLLM_ARGS+=(--enforce-eager)
JOB_LOG_DIR="$FL_ROOT/logs/select-$SLURM_JOB_ID"; mkdir -p "$JOB_LOG_DIR"
if [ -n "${SIF:-}" ]; then
  apptainer exec --nv --bind="$(csc-common-bind)" --bind="$TMPDIR" "$SIF" vllm "${VLLM_ARGS[@]}" \
    > "$JOB_LOG_DIR/vllm.log" 2>&1 &
else
  vllm "${VLLM_ARGS[@]}" > "$JOB_LOG_DIR/vllm.log" 2>&1 &
fi
VLLM_PID=$!
log "vLLM starting (pid $VLLM_PID, log $JOB_LOG_DIR/vllm.log)"
cleanup() {
  kill "$VLLM_PID" 2>/dev/null
  log "judge cache: $JUDGE_CACHE_DIR; reports: $OUT_DIR; job used $(( ($(date +%s) - T0) / 60 )) min"
}
trap cleanup EXIT
STOPPING=0
trap 'STOPPING=1; log "time limit in 5 min: stopping; answers so far are cached, submit the same command again"; kill -TERM "${SEL_PID:-}" 2>/dev/null' USR1

for i in $(seq 1 180); do
  if curl -sf --unix-socket "$SOCK" http://localhost/v1/models >/dev/null 2>&1; then break; fi
  kill -0 "$VLLM_PID" 2>/dev/null || { tail -30 "$JOB_LOG_DIR/vllm.log"; fail "vLLM exited during start-up"; }
  sleep 10
done
curl -sf --unix-socket "$SOCK" http://localhost/v1/models >/dev/null || fail "vLLM not ready after 30 min"
log "vLLM ready after $(( $(date +%s) - T0 ))s"

"${SF[@]}" python -m fl_tools select "reports/${RUNS[0]}" --judge-model "$FL_PRESET" --check-logprobs \
  | tee "$JOB_LOG_DIR/check-logprobs.txt" | tail -3

# ---------------------------------------------------------------- replays, one run after the other
RC=0
for r in "${RUNS[@]}"; do
  [ "$STOPPING" = 1 ] && break
  T_RUN=$(date +%s)
  log "=== $r: select $FL_SELECTORS"
  SEL=(python -m fl_tools select "reports/$r" --selector "$FL_SELECTORS" --judge-model "$FL_PRESET"
       --split "$FL_SPLIT" --shortlist "$FL_SHORTLIST" --k "$FL_K" --jobs "$FL_SEL_JOBS" --call-timeout "${FL_CALL_TIMEOUT:-120}"
       --cache "/work/judge/$r.jsonl" --out-root "$OUT_C" ${FL_EXTRA:-})
  "${SF[@]}" "${SEL[@]}" > "$JOB_LOG_DIR/$r-select.txt" 2>&1 &
  SEL_PID=$!
  wait "$SEL_PID"; rc=$?
  [ "$STOPPING" = 1 ] && wait "$SEL_PID" 2>/dev/null
  tail -40 "$JOB_LOG_DIR/$r-select.txt"
  if [ "$rc" != 0 ]; then log "select on $r failed (exit $rc), see $JOB_LOG_DIR/$r-select.txt"; RC=$rc; continue; fi
  if [ -n "$FL_LADDER" ]; then
    GATE=(python -m fl_tools gate "reports/$r" --ladder "$FL_LADDER" --split "$FL_SPLIT" --out-root "$OUT_C")
    [[ " ${FL_EXTRA:-} " == *" --reveal-test "* ]] && GATE+=(--reveal-test)
    "${SF[@]}" "${GATE[@]}" > "$JOB_LOG_DIR/$r-gate.txt" 2>&1 || log "gate on $r failed, see $JOB_LOG_DIR/$r-gate.txt"
    head -20 "$JOB_LOG_DIR/$r-gate.txt"
  fi
  E=$(( $(date +%s) - T_RUN ))
  python3 - "$OUT_DIR/$r-judge-job.json" <<PY
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception:
    data = {"jobs": []}
data["jobs"].append({"slurm_job_id": "$SLURM_JOB_ID", "node": "$(hostname)", "judge": "$FL_HF_REPO",
                     "served_name": "$FL_PRESET", "vllm_module": "$VLLM_MODULE", "selectors": "$FL_SELECTORS",
                     "ladder": "$FL_LADDER", "split": "$FL_SPLIT", "shortlist": "$FL_SHORTLIST", "k": $FL_K,
                     "parallel_bugs": $FL_SEL_JOBS, "elapsed_s": $E, "call_timeout_s": ${FL_CALL_TIMEOUT:-120},
                     "git_commit": "$(git -C "$FL_REPO" rev-parse HEAD 2>/dev/null || echo unknown)",
                     "gpu_billing_units_est": round($E / 3600 * 200, 1), "exit": $rc})
json.dump(data, open(path, "w"), indent=2)
PY
  log "$r done in $(( E / 60 )) min (about $(( E * 200 / 3600 )) GPU BU)"
done
log "all runs done; total job time $(( ($(date +%s) - T0) / 60 )) min (about $(( ($(date +%s) - T0) * 200 / 3600 )) GPU BU)"
exit "$RC"
