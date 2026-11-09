#!/usr/bin/env bash
# Smoke test of the whole pipeline before the official runs (execution plan 2026-11-09, step 3).
# 5 chosen bugs per dataset x {SoapFL, class widening always, class widening gated}, then ONE judge job on the six
# smoke runs. Bugs were picked to exercise the known failure paths, not to look good:
#   dataset 1: Lang-1 (failed in the old baseline because of the old cache bug), Math-14 (the bug that hung for
#              6 h in Nov 2026), Closure-115 + Mockito-1 (expected: no_failing_test_output), Chart-1 (normal)
#   dataset 2: Cli-1 (same old cache bug), Gson-14 (no result in every run), Closure-171 (model answer SoapFL
#              cannot parse), JacksonDatabind-8 (long method names), Jsoup-1 (normal)
#
#   bash csc/smoke_all.sh            submit the 6 front-end jobs (gpumedium, 40-min limit each)
#   bash csc/smoke_all.sh judge      after they finished: submit the judge job on the 6 smoke runs
#   bash csc/smoke_all.sh report     after the judge job: write reports/final/SMOKE_REPORT.md
#   add --dry-run to the first two to print the commands only
#
# Estimated cost (from the November job notes: about 1-2 min of work per bug with 5 workers, plus 1-2 min vLLM
# start and the first rebuild of each bug's test cache): about 6-12 min per front-end job = 20-40 BU each,
# 6 jobs = 120-240 BU; judge job about 5-10 BU. Total about 130-250 GPU BU.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
MODE="${1:-front}"; DRY=""
for a in "$@"; do [ "$a" = --dry-run ] && DRY=--dry-run; done
D1=Lang-1,Math-14,Closure-115,Mockito-1,Chart-1
D2=Cli-1,Gson-14,Closure-171,JacksonDatabind-8,Jsoup-1
RUNS=(smoke5-soapfl-d1 smoke5-ca3-d1 smoke5-ca3g-d1 smoke5-soapfl-d2 smoke5-ca3-d2 smoke5-ca3g-d2)

case "$MODE" in
  front|--dry-run)
    for ds in d1 d2; do
      if [ "$ds" = d1 ]; then SEL=$D1; EXTRA=(); else SEL=$D2; EXTRA=(--dataset d4j2new); fi
      for setting in soapfl ca3 ca3g; do
        case "$setting" in soapfl) P=() ;; ca3) P=(--classaug --ca-mode always) ;; ca3g) P=(--classaug --ca-mode gated) ;; esac
        # --retries 0 = the official protocol (no reruns); partition gpumedium so the job is the same as a real one
        bash csc/submit.sh qwen25coder --select "$SEL" "${EXTRA[@]}" "${P[@]}" --name "smoke5-$setting-$ds" \
          --retries 0 --partition gpumedium --time 00:40:00 $DRY
      done
    done ;;
  judge)
    bash csc/submit_select.sh qwen25coder "$(IFS=,; echo "${RUNS[*]}")" --name smoke5-judge --time 00:30:00 $DRY ;;
  report)
    source csc/config.sh
    python3 scripts/final/smoke_report.py "${RUNS[@]}" --logs "$FL_ROOT/logs" --judge-root "$FL_ROOT/judge-vllm" ;;
  *) sed -n 2,20p "$0"; exit 2 ;;
esac
