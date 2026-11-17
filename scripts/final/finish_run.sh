#!/usr/bin/env bash
# finish_run.sh -- pack finished runs into ONE archive, check it, delete the folders, log the storage.
# Runs on a Roihu login node. Put it in the repo as scripts/final/finish_run.sh.
#
#   finish_run.sh check  <label>              write the storage numbers to the log (use after EVERY model run)
#   finish_run.sh list                        show every run in results/ and how many files+folders it uses
#   finish_run.sh pack   <name> [<run>...]    make ONE archive named <name> from one or more runs (deletes NOTHING)
#                                             with only <name> given, <name> is also the run folder name
#   finish_run.sh confirm <name>              compare checksums from your own copy (paste them in, end with Ctrl-D)
#   finish_run.sh delete <name>               delete the run folders (only after confirm; you must type <name>)
#
# <run> is a folder name inside results/, for example runall-qwen25coder-csc-r1
# The archive holds, for every run: results/<run>, the replay folders judge-vllm/<run>-sel-*,
# the judge answer cache judge-cache/<run>.jsonl and the small summary files judge-vllm/<run>*.
# 'delete' removes only results/<run> and the replay folders; the judge cache and summaries stay.
set -euo pipefail

FL="${FL:-/scratch/project_2021789/andreist/fl}"
RESULTS="$FL/results"
JUDGE="$FL/judge-vllm"
JCACHE="$FL/judge-cache"
ARCH="$FL/archive"          # the archives (a handful of files)
SMALL="$FL/small-tables"    # small tables to copy into git
LOG="$FL/storage-log.tsv"
WARN_ENTRIES=300000         # warn above this (60% of 500,000)

die() { echo "ERROR: $*" >&2; exit 1; }

usage() { sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

check_name() {
  [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || die "bad name: '$1'"
}

replay_dirs() {   # replay folders that belong to this run: judge-vllm/<run>-sel-*
  find "$JUDGE" -maxdepth 1 -type d -name "${1}-sel-*" 2>/dev/null | sort
}

entries() {       # number of files + folders under the given paths (this is what the quota counts)
  find "$@" 2>/dev/null | wc -l
}

to_number() {     # 174K -> 174000
  awk -v u="$1" 'BEGIN{ if (u ~ /K$/) {sub(/K/,"",u); print u*1000}
                        else if (u ~ /M$/) {sub(/M/,"",u); print u*1000000}
                        else print u }'
}

cmd_check() {
  local label="${1:-manual}" line space files used num
  line=$(csc-workspaces 2>/dev/null | awk '/^\/scratch\//{print $2" "$3}') || true
  [[ -n "$line" ]] || die "could not read csc-workspaces"
  space=${line%% *}; files=${line##* }
  mkdir -p "$(dirname "$LOG")"
  printf '%s\t%s\t%s\t%s\n' "$(date +%F)" "$label" "$space" "$files" >> "$LOG"
  echo "STORAGE (scratch): space $space   files+folders $files"
  echo "Paste this line into the storage log in the roadmap:"
  echo "| $(date +%F) | $label | ${space%%/*} / ${files%%/*} | |"
  used=${files%%/*}; num=$(to_number "$used")
  if (( num > WARN_ENTRIES )); then
    echo "WARNING: more than $WARN_ENTRIES files+folders used. Pack and delete finished runs now."
  fi
}

cmd_list() {
  printf '%10s  %s\n' "entries" "run"
  for d in "$RESULTS"/*/; do
    [[ -d "$d" ]] || continue
    n=$(basename "$d")
    printf '%10s  %s  (replay folders: %s)\n' "$(entries "$d")" "$n" "$(replay_dirs "$n" | wc -l)"
  done
}

cmd_pack() {
  local name="$1"; shift
  check_name "$name"
  local runs=("$@")
  (( ${#runs[@]} > 0 )) || runs=("$name")
  mkdir -p "$ARCH" "$SMALL/$name"

  local del=() keep=() r
  for r in "${runs[@]}"; do
    check_name "$r"
    [[ -d "$RESULTS/$r" ]] || die "no such run folder: $RESULTS/$r"
    del+=("results/$r")
    local d
    while IFS= read -r d; do [[ -n "$d" ]] && del+=("judge-vllm/$(basename "$d")"); done < <(replay_dirs "$r")
    [[ -f "$JCACHE/$r.jsonl" ]] && keep+=("judge-cache/$r.jsonl")
    local f
    while IFS= read -r f; do [[ -n "$f" ]] && keep+=("judge-vllm/$(basename "$f")"); done \
      < <(find "$JUDGE" -maxdepth 1 -type f -name "${r}*" 2>/dev/null | sort)
  done
  local all=("${del[@]}" "${keep[@]}")

  # lists used later (paths are relative to $FL)
  printf '%s\n' "${all[@]}" > "$ARCH/$name.paths"
  printf '%s\n' "${del[@]}" > "$ARCH/$name.delete"

  local expected; expected=$(cd "$FL" && find "${all[@]}" | wc -l)
  echo "Archive: $name"
  echo "  runs: ${runs[*]}"
  echo "  to pack: ${#all[@]} paths, $expected files+folders in total"
  echo "  (of which $(cd "$FL" && find "${del[@]}" | wc -l) will be freed by 'delete')"

  # 1. small tables: every top-level file of each run folder and of each replay folder
  echo "[1/4] copying small tables to $SMALL/$name"
  for r in "${runs[@]}"; do
    mkdir -p "$SMALL/$name/$r"
    find "$RESULTS/$r" -maxdepth 1 -type f -size -5M -exec cp -p {} "$SMALL/$name/$r/" \;
    find "$JUDGE" -maxdepth 1 -type f -name "${r}*" -size -5M -exec cp -p {} "$SMALL/$name/$r/" \; 2>/dev/null || true
    local rd
    while IFS= read -r rd; do
      [[ -n "$rd" ]] || continue
      mkdir -p "$SMALL/$name/$r/replays/$(basename "$rd")"
      find "$rd" -maxdepth 1 -type f -size -5M -exec cp -p {} "$SMALL/$name/$r/replays/$(basename "$rd")/" \;
    done < <(replay_dirs "$r")
  done
  echo "      $(find "$SMALL/$name" -type f | wc -l) small files copied"

  # 2. the archive (gzip level 1: fast; 'nice' so the login node is not overloaded)
  echo "[2/4] packing (one archive file)"
  nice tar -C "$FL" -cf - -T "$ARCH/$name.paths" | gzip -1 > "$ARCH/$name.tar.gz.part"
  mv "$ARCH/$name.tar.gz.part" "$ARCH/$name.tar.gz"

  # 3. verify: readable, and lists exactly as many entries as the folders have
  echo "[3/4] checking the archive"
  gzip -t "$ARCH/$name.tar.gz" || die "archive is damaged: $name.tar.gz"
  local got; got=$(tar -tzf "$ARCH/$name.tar.gz" | wc -l)
  [[ "$got" == "$expected" ]] || die "entry count differs (folders $expected, archive $got)"

  # 4. checksum + manifest
  echo "[4/4] writing checksum and manifest"
  ( cd "$ARCH" && sha256sum "$name.tar.gz" > "$name.sha256" )
  {
    echo "archive: $name.tar.gz   created: $(date -Is)   entries: $expected"
    echo "extract with: tar -xzf $name.tar.gz   (creates results/ judge-vllm/ judge-cache/ in the current folder)"
    local p
    for p in "${all[@]}"; do printf '%8s  %s\n' "$(cd "$FL" && find "$p" | wc -l)" "$p"; done
  } > "$ARCH/$name.manifest.txt"
  rm -f "$ARCH/$name.confirmed"   # a new pack cancels any older confirmation
  cat "$ARCH/$name.sha256"
  ls -lh "$ARCH/$name.tar.gz"

  cat <<EOF

NOTHING WAS DELETED. Next steps (on your Ubuntu computer):
  1. mkdir -p ~/thesis-archive && cd ~/thesis-archive
  2. scp andreist@roihu-gpu.csc.fi:$ARCH/$name.tar.gz andreist@roihu-gpu.csc.fi:$ARCH/$name.sha256 andreist@roihu-gpu.csc.fi:$ARCH/$name.manifest.txt .
  3. sha256sum -c $name.sha256          (must print OK)
     tar -tzf $name.tar.gz | wc -l       (must print $expected)
  4. Upload $name.tar.gz to your cloud.
  5. Tell Roihu that the copy is good (run on your computer, in the same folder):
       sha256sum $name.tar.gz | ssh andreist@roihu-gpu.csc.fi 'bash <repo>/scripts/final/finish_run.sh confirm $name'
  6. Only then, on Roihu:  finish_run.sh delete $name
EOF
  cmd_check "packed $name (nothing deleted yet)"
}

cmd_confirm() {
  local name="$1"; check_name "$name"
  [[ -f "$ARCH/$name.sha256" ]] || die "no checksum file; run pack first"
  echo "Paste the line of your local sha256sum output, then press Ctrl-D (or pipe it in)."
  local mine; mine=$(awk 'NF>=2{print $1, $2}' | sort)
  [[ -n "$mine" ]] || die "no checksum received"
  local stored; stored=$(awk 'NF>=2{print $1, $2}' "$ARCH/$name.sha256" | sort)
  if [[ "$mine" == "$stored" ]]; then
    date -Is > "$ARCH/$name.confirmed"
    echo "OK: your copy matches. $name is confirmed and may be deleted."
  else
    echo "--- stored on Roihu"; echo "$stored"; echo "--- yours"; echo "$mine"
    die "checksums differ. NOT confirmed. Copy the archive again."
  fi
}

cmd_delete() {
  local name="$1"; check_name "$name"
  [[ -f "$ARCH/$name.confirmed" ]] || die "not confirmed. Run pack, copy, then confirm first."
  [[ -f "$ARCH/$name.delete" ]] || die "no delete list for $name"
  ( cd "$ARCH" && sha256sum -c "$name.sha256" ) || die "archive on Roihu no longer matches its checksum"
  local victims=() p
  while IFS= read -r p; do
    [[ -n "$p" ]] || continue
    [[ "$p" =~ ^(results|judge-vllm)/[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || die "refusing odd path in delete list: $p"
    victims+=("$FL/$p")
  done < "$ARCH/$name.delete"
  echo "This will DELETE (the archive stays; judge-cache and the small summary files stay):"
  local v
  for v in "${victims[@]}"; do
    [[ -e "$v" ]] && echo "  $v   ($(entries "$v") files+folders)"
  done
  local ans; read -r -p "Type the archive name ($name) to confirm: " ans
  [[ "$ans" == "$name" ]] || die "name did not match. Nothing deleted."
  for v in "${victims[@]}"; do rm -rf --one-file-system -- "$v"; done
  echo "Deleted."
  cmd_check "deleted $name (archive kept)"
}

[[ $# -ge 1 ]] || usage
case "$1" in
  check)   cmd_check "${2:-manual}" ;;
  list)    cmd_list ;;
  pack)    [[ $# -ge 2 ]] || usage; shift; cmd_pack "$@" ;;
  confirm) [[ $# -eq 2 ]] || usage; cmd_confirm "$2" ;;
  delete)  [[ $# -eq 2 ]] || usage; cmd_delete "$2" ;;
  *)       usage ;;
esac
