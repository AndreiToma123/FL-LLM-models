#!/usr/bin/env bash
# Serve an open model through vLLM's OpenAI-compatible API.
# Usage: scripts/serve_vllm.sh [model] [port]
set -euo pipefail
MODEL="${1:-${SOAPFL_MODEL_NAME:-Qwen/Qwen2.5-Coder-7B-Instruct}}"
PORT="${2:-8000}"
CTX="${SOAPFL_CONTEXT_LIMIT:-32768}"
exec python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --served-model-name "$MODEL" \
  --max-model-len "$CTX" --port "$PORT" \
  --gpu-memory-utilization "${GPU_MEM_UTIL:-0.90}" \
  --dtype auto
