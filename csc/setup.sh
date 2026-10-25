#!/usr/bin/env bash
# One-time setup on CSC Roihu. Run on the GPU LOGIN node (roihu-gpu.csc.fi): GPU nodes are ARM,
# and an image built on the x86 CPU side would not run there. Login nodes cost no billing units.
#
#   csc/setup.sh check            what is there and what is missing
#   csc/setup.sh dirs             create the folders under $FL_ROOT
#   csc/setup.sh image            build the SoapFL + Defects4J Apptainer image (~30-60 min, several GB)
#   csc/setup.sh model <preset>   download the preset's Hugging Face weights (e.g. qwen25coder)
#   csc/setup.sh all <preset>     dirs + image + model
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
cd "$FL_REPO"

die() { echo "ERROR: $*" >&2; exit 1; }

need_arm() {
  [ "$(uname -m)" = "aarch64" ] || die "this machine is $(uname -m). Log in to roihu-gpu.csc.fi (ARM) for this step."
}

preset_field() {   # preset_field <preset> <field>
  python3 - "$FL_REPO/configs/models.json" "$1" "$2" <<'PY'
import json, sys
presets = json.load(open(sys.argv[1]))
p = presets.get(sys.argv[2])
if p is None or sys.argv[2].startswith("_"):
    sys.exit(f"unknown preset {sys.argv[2]!r}; known: {', '.join(k for k in presets if not k.startswith('_'))}")
v = p.get(sys.argv[3])
print("" if v is None else (json.dumps(v) if isinstance(v, (dict, list)) else v))
PY
}

model_dir() { echo "$MODELS_DIR/$(echo "$1" | tr '/' '_')"; }

cmd_dirs() {
  local parent; parent="$(dirname "$FL_ROOT")"
  if [ ! -d "$(dirname "$parent")" ]; then
    die "$(dirname "$parent") does not exist. Run 'csc-workspaces' to see your project's scratch path and set FL_ROOT accordingly."
  fi
  mkdir -p "$FL_ROOT"/{images,models,results,soapfl-cache,hf-cache,logs}
  echo "folders ready under $FL_ROOT"
}

cmd_image() {
  need_arm
  command -v apptainer >/dev/null || die "apptainer not found on this node"
  cmd_dirs
  local tmp="${TMPDIR:-/tmp}"
  export APPTAINER_CACHEDIR="$tmp/apptainer-cache"
  local out="$SOAPFL_SIF"
  echo "building $out from csc/soapfl.def (this downloads several GB; logs in $FL_ROOT/logs/build-image.log)"
  apptainer build --fakeroot --force --bind="$tmp:/tmp" "$out.partial" csc/soapfl.def 2>&1 | tee "$FL_ROOT/logs/build-image.log"
  mv -f "$out.partial" "$out"
  apptainer test "$out"
  echo "image ready: $out ($(du -h "$out" | cut -f1))"
}

cmd_model() {
  local preset="${1:-}"; [ -n "$preset" ] || die "usage: csc/setup.sh model <preset>"
  local repo; repo="$(preset_field "$preset" hf)"
  [ -n "$repo" ] || die "preset $preset has no 'hf' field in configs/models.json (no Hugging Face repo set)"
  local dest; dest="$(model_dir "$repo")"
  mkdir -p "$dest" "$HF_HOME"
  module purge >/dev/null 2>&1 || true
  module load "$VLLM_MODULE"
  echo "downloading $repo -> $dest (set HF_TOKEN first if the repo is gated)"
  python - "$repo" "$dest" <<'PY'
import sys
from huggingface_hub import snapshot_download
repo, dest = sys.argv[1], sys.argv[2]
snapshot_download(repo_id=repo, local_dir=dest,
                  allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.tiktoken", "*.py", "*.jinja"])
print("done")
PY
  du -sh "$dest"
}

cmd_check() {
  echo "arch:            $(uname -m)  (must be aarch64 for the image step)"
  echo "project:         $CSC_PROJECT"
  echo "FL_ROOT:         $FL_ROOT $( [ -d "$FL_ROOT" ] && echo '(exists)' || echo '(MISSING: csc/setup.sh dirs)')"
  echo "SoapFL image:    $SOAPFL_SIF $( [ -f "$SOAPFL_SIF" ] && echo '(exists)' || echo '(MISSING: csc/setup.sh image)')"
  if [ -f "$SOAPFL_SIF" ]; then
    local in_img repo_sum
    in_img="$(apptainer exec "$SOAPFL_SIF" cut -d' ' -f1 /opt/fl/patch.sha256 2>/dev/null || true)"
    repo_sum="$(sha256sum patches/0001-open-model-support.patch | cut -d' ' -f1)"
    [ "$in_img" = "$repo_sum" ] && echo "patch:           image matches the repository" \
      || echo "patch:           image was built from a DIFFERENT patch: rebuild with csc/setup.sh image"
  fi
  for preset in $(python3 -c "import json;print(' '.join(k for k in json.load(open('configs/models.json')) if not k.startswith('_')))"); do
    local repo; repo="$(preset_field "$preset" hf)"
    if [ -z "$repo" ]; then echo "model $preset: no hf repo (local only)"; continue; fi
    local d; d="$(model_dir "$repo")"
    if ls "$d"/*.safetensors >/dev/null 2>&1; then echo "model $preset: $repo ready ($(du -sh "$d" | cut -f1))"
    else echo "model $preset: $repo not downloaded (csc/setup.sh model $preset)"; fi
  done
  command -v csc-workspaces >/dev/null && csc-workspaces || true
}

case "${1:-check}" in
  check) cmd_check ;;
  dirs)  cmd_dirs ;;
  image) cmd_image ;;
  model) shift; cmd_model "$@" ;;
  all)   shift; cmd_dirs; cmd_image; cmd_model "${1:-qwen25coder}" ;;
  *) sed -n 2,10p "$0"; exit 2 ;;
esac
