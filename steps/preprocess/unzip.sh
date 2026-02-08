#!/usr/bin/env bash
set -euo pipefail
# Extract tar files from DatasetDownload/ to raw/.
# Usage: ./unzip.sh DATA_ROOT [--start_stage N] [--stop_stage N] [--splits SPLIT1 ...]

# ── Positional args ──
DATA_ROOT="${1:?Error: DATA_ROOT is required (arg 1)}"; shift

# ── Defaults ──
START_STAGE=1; STOP_STAGE=2
SPLITS=("Train" "Dev")

# ── Parse ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --start_stage) START_STAGE="$2"; shift 2 ;;
        --stop_stage)  STOP_STAGE="$2";  shift 2 ;;
        --splits)
            SPLITS=(); shift
            while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do SPLITS+=("$1"); shift; done ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# ── Validate ──
[[ "$START_STAGE" =~ ^[12]$ ]] && [[ "$STOP_STAGE" =~ ^[12]$ ]] && [[ $START_STAGE -le $STOP_STAGE ]] \
    || { echo "Error: stages must be 1 or 2, start <= stop"; exit 1; }

# ── Run ──
echo "Splits: ${SPLITS[*]}, Stages: ${START_STAGE}-${STOP_STAGE}"
mkdir -p "${DATA_ROOT}/raw"

for split in "${SPLITS[@]}"; do
    src="${DATA_ROOT}/DatasetDownload/${split}"
    tgt="${DATA_ROOT}/raw/${split}"
    [[ ! -d "$src" ]] && echo "Warning: $src not found, skipping" && continue
    mkdir -p "$tgt"

    # Stage 1: Extract first-level tar files
    if [[ $START_STAGE -le 1 ]] && [[ $STOP_STAGE -ge 1 ]]; then
        find "$src" -maxdepth 1 -name "*.tar" ! -name "*Json.tar" -print0 | while IFS= read -r -d '' f; do
            echo "Extracting: $(basename "$f")"
            tar -xf "$f" -C "$tgt"
        done
    fi

    # Stage 2: Extract nested tar files (one per speaker)
    if [[ $START_STAGE -le 2 ]] && [[ $STOP_STAGE -ge 2 ]]; then
        find "$tgt" -maxdepth 1 -name "*.tar" -print0 | while IFS= read -r -d '' f; do
            echo "Extracting speaker tar: $(basename "$f")"
            tar -xf "$f" -C "$tgt" && rm -f "$f"
        done
    fi
done

echo "Done."
