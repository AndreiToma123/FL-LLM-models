#!/bin/bash
# One CSC Roihu job = one GPU running vLLM + many SoapFL workers on the same node.
# Submit it with csc/submit.sh (which sets account, partition, time and the job settings file).
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=72
#SBATCH --mem=217000M
#SBATCH --signal=B:USR1@600
set -uo pipefail

: "${FL_JOB_ENV:?submit this job with csc/submit.sh}"
source "$FL_JOB_ENV"
source "$FL_REPO/csc/config.sh"

T0=$(date +%s)
log() { echo "[$(date +%H:%M:%S)] $*"; }
fail() { log "FAILED: $*"; exit 1; }

RUN="$FL_RUN"
PERSIST="$RESULTS_DIR/$RUN"                       # survives the job (scratch)
WORK="${TMPDIR:?}/fl-$SLURM_JOB_ID"               # fast node-local disk, deleted after the job
JOB_LOGS="$PERSIST/_jobs/$SLURM_JOB_ID"
mkdir -p "$WORK/results/$RUN" "$WORK/cache" "$PERSIST" "$SOAPFL_CACHE" "$JOB_LOGS" || fail "cannot create folders"
log "job $SLURM_JOB_ID on $(hostname): run $RUN, preset $FL_PRESET ($FL_HF_REPO), partition $SLURM_JOB_PARTITION"

# ---------------------------------------------------------------- resume + cache
# Bugs finished by earlier jobs of this run are copied in and skipped by the runner (result.json exists).
rsync -a "$PERSIST/" "$WORK/results/$RUN/" --exclude _jobs
# SoapFL's per-bug failing-test cache does not depend on the model: reuse it across runs.
# Keep ALL of tmp/: with test_failure.pkl present SoapFL skips re-running the failing tests, but its class step
# still READS tmp/<suite>/<test>/stack_trace.txt and re-uses the instrumentation logs inst_src.log / run_src.log
# ("instrumentation already done"). Without those logs it re-instruments on a checkout it never compiled:
# all Mockito bugs then fail ("No instrument file") and Math-14 hung 2 x 3 h (HypoDeduce run of 2026-11-01).
# Excluding all of tmp/ made repeated runs crash outright (FileNotFoundError, class-augmentation runs).
CACHE_FILTER=(--exclude '*.partial')   # (non-empty: an empty array trips set -u in older bash)
rsync -a "${CACHE_FILTER[@]}" "$SOAPFL_CACHE/" "$WORK/cache/"
# self-heal entries saved by older jobs without tmp/ or without the instrumentation logs: remove the WHOLE entry
# (only in this job's copy), so SoapFL rebuilds it from scratch: compile, run the failing tests, instrument (one slower
# first run per bug). Dropping only the pickle is not enough: SoapFL then sees stack_trace.txt, skips the compile
# ("test already run") and instruments an uncompiled checkout (Mockito: no run_test.log, 2026-11-02).
HEALED=0
for d in "$WORK"/cache/*/; do
  if [ -z "$(find "${d}tmp" -name stack_trace.txt -print -quit 2>/dev/null)" ] \
     || [ -z "$(find "${d}tmp" -name inst_test.log -print -quit 2>/dev/null)" ]; then
    rm -rf "$d"; HEALED=$((HEALED + 1))
  fi
done
log "cache: $(ls -d "$WORK"/cache/*/ 2>/dev/null | wc -l) bug entries restored, $HEALED incomplete (no failing-test traces or instrumentation logs) and will be rebuilt from scratch"

sync_back() {
  rsync -a --exclude 'buggy/' --exclude 'fixed/' "$WORK/results/$RUN/" "$PERSIST/"
  rsync -a "${CACHE_FILTER[@]}" "$WORK/cache/" "$SOAPFL_CACHE/"
}

# ---------------------------------------------------------------- vLLM server
module purge
module load "$VLLM_MODULE" || fail "module $VLLM_MODULE not available (module spider python-vllm)"
SOCK="$TMPDIR/vllm-$SLURM_JOB_ID.sock"          # Unix socket: only our processes can reach the server
if [ "${#SOCK}" -gt 100 ]; then                    # Unix socket paths are limited to ~107 characters
  SOCK_DIR="/tmp/fl-$USER-$SLURM_JOB_ID"; mkdir -p "$SOCK_DIR"; chmod 700 "$SOCK_DIR"; SOCK="$SOCK_DIR/vllm.sock"
fi
export HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCHINDUCTOR_CACHE_DIR="$TMPDIR/torch-cache"
VLLM_ARGS=(serve "$FL_MODEL_DIR" --served-model-name "$FL_PRESET" --uds "$SOCK"
           --max-model-len "$FL_CTX" --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0)
[ "${FL_ENFORCE_EAGER:-0}" = 1 ] && VLLM_ARGS+=(--enforce-eager)
if [ -n "${SIF:-}" ]; then                         # the module provides its container in $SIF (CSC example)
  apptainer exec --nv --bind="$(csc-common-bind)" --bind="$TMPDIR" "$SIF" vllm "${VLLM_ARGS[@]}" \
    > "$JOB_LOGS/vllm.log" 2>&1 &
else
  vllm "${VLLM_ARGS[@]}" > "$JOB_LOGS/vllm.log" 2>&1 &
fi
VLLM_PID=$!
log "vLLM starting (pid $VLLM_PID, log $JOB_LOGS/vllm.log)"

cleanup() {
  if [ -n "${SYNC_PID:-}" ]; then pkill -P "$SYNC_PID" 2>/dev/null; kill "$SYNC_PID" 2>/dev/null; fi
  kill "$VLLM_PID" 2>/dev/null
  sync_back
  log "saved to $PERSIST; job used $(( ($(date +%s) - T0) / 60 )) min"
}
trap cleanup EXIT

for i in $(seq 1 180); do                          # up to 30 min for loading the weights
  if curl -sf --unix-socket "$SOCK" http://localhost/v1/models >/dev/null 2>&1; then break; fi
  kill -0 "$VLLM_PID" 2>/dev/null || { tail -30 "$JOB_LOGS/vllm.log"; fail "vLLM exited during start-up"; }
  sleep 10
done
curl -sf --unix-socket "$SOCK" http://localhost/v1/models >/dev/null || fail "vLLM not ready after 30 min"
T_READY=$(date +%s)
log "vLLM ready after $(( T_READY - T0 ))s"

# ---------------------------------------------------------------- how many parallel bugs
CPUS="${SLURM_CPUS_PER_TASK:-72}"
MEM_GIB=$(( ${SLURM_MEM_PER_NODE:-217000} / 1024 ))
[ "$MEM_GIB" -gt "$HOST_MEM_GIB" ] && MEM_GIB="$HOST_MEM_GIB"
DISK_GIB=$(df -BG --output=avail "$TMPDIR" | tail -1 | tr -dc '0-9')
BY_CPU=$(( (CPUS - RESERVED_CORES) / CORES_PER_WORKER ))
BY_MEM=$(( (MEM_GIB - RESERVED_MEM_GIB) / MEM_GIB_PER_WORKER ))
BY_DISK=$(( DISK_GIB / 3 ))                        # two checkouts + build output per running bug
if [ "$FL_JOBS" = auto ]; then
  JOBS=$(printf '%s\n' "$BY_CPU" "$BY_MEM" "$BY_DISK" "$MAX_WORKERS" | sort -n | head -1)
  [ "$JOBS" -lt 1 ] && JOBS=1
else
  JOBS="$FL_JOBS"
fi
log "workers: $JOBS (limits: cpu $BY_CPU, memory $BY_MEM, disk $BY_DISK, max $MAX_WORKERS)"

# ---------------------------------------------------------------- SoapFL in its container
{
  printf 'SOAPFL_UDS=%q\n' "$SOCK"
  printf 'SOAPFL_BASE_URL=%q\n' "http://localhost/v1"
  printf 'SOAPFL_API_KEY=%q\n' "EMPTY"
  printf 'SOAPFL_MODEL_NAME=%q\n' "$FL_PRESET"
  printf 'SOAPFL_CONTEXT_LIMIT=%q\n' "$FL_CTX"
  printf 'SOAPFL_MAX_COMPLETION_TOKENS=%q\n' "$FL_MAX_TOKENS"
  [ "$FL_EXTRA_BODY" != "{}" ] && printf 'SOAPFL_EXTRA_BODY=%q\n' "$FL_EXTRA_BODY"
  printf 'TMPDIR=%q\n' "$TMPDIR"
} > "$WORK/soapfl.env"
SF=(apptainer exec --cleanenv --writable-tmpfs --env-file "$WORK/soapfl.env"
    --bind="$(csc-common-bind)" --bind="$TMPDIR" --bind="$WORK/cache:/opt/SoapFL/cache"
    --bind="$FL_REPO:/work/repo" --pwd /work/repo "$SOAPFL_SIF")

"${SF[@]}" python -m fl_tools preflight --dataset "${FL_DATASET:-d4j14}" | tee "$JOB_LOGS/preflight.txt"
[ "${PIPESTATUS[0]}" = 0 ] || fail "preflight failed (see above)"

if [ -n "$FL_SELECT" ]; then SELECTION=(--bugs "$FL_SELECT")
elif [ "$FL_N" = all ] || [ "$FL_N" = 0 ]; then SELECTION=()
else SELECTION=(--pilot "$FL_N" --sample-seed 0); fi   # same stratified sample as the local pipeline

( while sleep 300; do sync_back; done ) &
SYNC_PID=$!

STOPPING=0
on_time_limit() {
  STOPPING=1
  log "time limit in 10 min: stopping workers, progress is saved and resumable (submit the same command again)"
  kill -TERM "$RUN_PID" 2>/dev/null
}
trap on_time_limit USR1

T_RUN=$(date +%s)
"${SF[@]}" python -m fl_tools run --name "$RUN" --results-dir "$WORK/results" "${SELECTION[@]}" \
  --jobs "$JOBS" --seed "$FL_SEED" --timeout 3600 --skip-preflight ${FL_PIPELINE_ARGS:-} &
RUN_PID=$!
wait "$RUN_PID"; RC=$?
[ "$STOPPING" = 1 ] && wait "$RUN_PID" 2>/dev/null
T_END=$(date +%s)
log "runner finished (exit $RC) after $(( (T_END - T_RUN) / 60 )) min"

# ---------------------------------------------------------------- record the job, analyse, export
GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
python3 - "$WORK/results/$RUN/job_meta.json" <<PY
import json, os, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception:
    data = {"jobs": []}
elapsed = $T_END - $T0
data["jobs"].append({
    "slurm_job_id": "$SLURM_JOB_ID", "partition": "$SLURM_JOB_PARTITION", "node": "$(hostname)",
    "gpu": "$GPU_INFO", "gpus": 1, "cpus": $CPUS, "workers": $JOBS,
    "vllm_module": "$VLLM_MODULE", "model": "$FL_HF_REPO", "served_name": "$FL_PRESET",
    "context": $FL_CTX, "max_completion_tokens": $FL_MAX_TOKENS, "seed": $FL_SEED,
    "enforce_eager": "$FL_ENFORCE_EAGER" == "1",
    "started": $T0, "vllm_ready_s": $T_READY - $T0, "run_s": $T_END - $T_RUN, "elapsed_s": elapsed,
    "gpu_billing_units_est": round(elapsed / 3600 * 200, 1), "runner_exit": $RC,
    "stopped_by_time_limit": $STOPPING == 1,
})
json.dump(data, open(path, "w"), indent=2)
PY

for step in score funnel ties; do
  "${SF[@]}" python -m fl_tools "$step" "$WORK/results/$RUN" > "$JOB_LOGS/$step.txt" 2>&1 \
    || log "$step failed (see $JOB_LOGS/$step.txt)"
done
sync_back
"${SF[@]}" python -m fl_tools export "$WORK/results/$RUN" --dest "/work/repo/reports/$RUN" \
  || log "export failed"
cat "$JOB_LOGS/score.txt" 2>/dev/null | head -25
log "report: $FL_REPO/reports/$RUN   (copy it to your PC or commit it from here)"
exit "$RC"
