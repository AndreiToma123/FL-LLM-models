#!/usr/bin/env bash
# Clone SoapFL at the pinned commit, apply the open-model patch, build a venv.
# Usage: scripts/setup_soapfl.sh [python-executable]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${1:-python3}"
SOAPFL_COMMIT="c9f75f4f349849bc84d5cc50c4cc7dc70f012f16"
DEST="$ROOT/external/SoapFL"

mkdir -p "$ROOT/external"
if [ ! -d "$DEST/.git" ]; then
  git clone https://github.com/IntHelloWorld/SoapFL.git "$DEST"
fi
git -C "$DEST" fetch --quiet origin || true
git -C "$DEST" checkout --quiet "$SOAPFL_COMMIT"

if [ -f "$DEST/camel/local_llm.py" ]; then
  echo "patch already applied"
else
  git -C "$DEST" apply --whitespace=nowarn "$ROOT/patches/0001-open-model-support.patch"
  echo "patch applied"
fi

if [ ! -d "$ROOT/.venv" ]; then
  "$PYTHON" -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/pip" install --quiet --upgrade pip
"$ROOT/.venv/bin/pip" install --quiet -r "$ROOT/requirements.txt"

# Warm the tiktoken cache so compute nodes without internet can count tokens.
export TIKTOKEN_CACHE_DIR="${TIKTOKEN_CACHE_DIR:-$ROOT/.cache/tiktoken}"
mkdir -p "$TIKTOKEN_CACHE_DIR"
"$ROOT/.venv/bin/python" - <<'PY' || echo "WARNING: could not warm tiktoken cache (no internet?). SoapFL will fall back to a rough token estimate."
import tiktoken
tiktoken.get_encoding("cl100k_base")
print("tiktoken cache warmed")
PY

cat <<MSG

SoapFL ready in $DEST (commit $SOAPFL_COMMIT + patch).
Next: install Defects4J (scripts/install_defects4j.sh), copy $DEST/Defects4J_mod over it,
then: source configs/example.env (after editing) and run  python -m fl_tools preflight
MSG
