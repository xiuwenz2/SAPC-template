#!/usr/bin/env bash
set -euo pipefail
# Resample audio, copy JSONs, generate manifests, normalize references.
# Usage: ./preprocess.sh CONDA_ENV_NAME DATA_ROOT PROJ_ROOT [OPTIONS]
#   Stages: 1=resample, 2=copy JSON, 3=generate manifest, 4=normalize refs

# ── Positional args ──
CONDA_ENV_NAME="${1:?Error: CONDA_ENV_NAME is required (arg 1)}"; shift
DATA_ROOT="${1:?Error: DATA_ROOT is required (arg 2)}"; shift
PROJ_ROOT="${1:?Error: PROJ_ROOT is required (arg 3)}"; shift

# ── Defaults ──
START_STAGE=4; STOP_STAGE=4
SPLITS=("Train" "Dev")
TARGET_SR=16000; WORKERS=32

# ── Parse ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --start_stage) START_STAGE="$2"; shift 2 ;;
        --stop_stage)  STOP_STAGE="$2";  shift 2 ;;
        --sr)          TARGET_SR="$2";   shift 2 ;;
        --workers)     WORKERS="$2";     shift 2 ;;
        --splits)
            SPLITS=(); shift
            while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do SPLITS+=("$1"); shift; done ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# ── Validate ──
[[ "$START_STAGE" =~ ^[1234]$ ]] && [[ "$STOP_STAGE" =~ ^[1234]$ ]] && [[ $START_STAGE -le $STOP_STAGE ]] \
    || { echo "Error: stages must be 1-4, start <= stop"; exit 1; }

# ── Derived defaults ──
eval "$(conda shell.bash hook)"
conda activate "$CONDA_ENV_NAME"
PY="python3"; command -v python3 &>/dev/null || PY="python"

INPUT_ROOT="${DATA_ROOT}/raw"
OUTPUT_ROOT="${DATA_ROOT}/processed"
MANIFEST_DIR="${DATA_ROOT}/manifest"
mkdir -p "$OUTPUT_ROOT" "$MANIFEST_DIR"

echo "Splits: ${SPLITS[*]}, Stages: ${START_STAGE}-${STOP_STAGE}, Workers: ${WORKERS}"

# ── Stage 1: Resample audio ──
if [[ $START_STAGE -le 1 ]] && [[ $STOP_STAGE -ge 1 ]]; then
    RESAMPLE_PY="${PROJ_ROOT}/utils/resample.py"
    [[ -f "$RESAMPLE_PY" ]] || { echo "Error: $RESAMPLE_PY not found"; exit 1; }
    for split in "${SPLITS[@]}"; do
        echo "Resampling ${split} to ${TARGET_SR} Hz"
        "$PY" "$RESAMPLE_PY" \
            --input_dir "${INPUT_ROOT}/${split}" \
            --output_dir "${OUTPUT_ROOT}/${split}" \
            --sr "$TARGET_SR" \
            --workers "$WORKERS" \
            --skip-existing
    done
fi

# ── Stage 2: Copy JSON files from raw/ to processed/ ──
if [[ $START_STAGE -le 2 ]] && [[ $STOP_STAGE -ge 2 ]]; then
    for split in "${SPLITS[@]}"; do
        raw_dir="${INPUT_ROOT}/${split}"
        out_dir="${OUTPUT_ROOT}/${split}"
        [[ ! -d "$raw_dir" ]] && echo "Warning: $raw_dir not found, skipping" && continue
        echo "Copying JSON files for ${split}"
        find "$raw_dir" -name "*.json" -type f | while IFS= read -r json_file; do
            rel="${json_file#$raw_dir/}"
            mkdir -p "${out_dir}/$(dirname "$rel")"
            cp "$json_file" "${out_dir}/$(dirname "$rel")/"
        done
    done
fi

# ── Stage 3: Generate manifest CSVs ──
if [[ $START_STAGE -le 3 ]] && [[ $STOP_STAGE -ge 3 ]]; then
    GEN_MAN_PY="${PROJ_ROOT}/utils/manifest.py"
    [[ -f "$GEN_MAN_PY" ]] || { echo "Error: $GEN_MAN_PY not found"; exit 1; }

    GITHUB_REPO="https://raw.githubusercontent.com/speechaccessibility/SplitTrainTest/main/SAPC2"
    for split in "${SPLITS[@]}"; do
        txt_file="${MANIFEST_DIR}/${split}.txt"
        if [[ ! -f "$txt_file" ]]; then
            split_lower=$(echo "$split" | tr '[:upper:]' '[:lower:]')
            echo "Downloading ${split}.txt from GitHub..."
            if command -v curl &>/dev/null; then
                http_code=$(curl -L -o "$txt_file" -w "%{http_code}" -s "${GITHUB_REPO}/${split_lower}.txt")
                [[ "$http_code" != "200" ]] && { echo "Error: download failed (HTTP $http_code)"; exit 1; }
            elif command -v wget &>/dev/null; then
                wget -qO "$txt_file" "${GITHUB_REPO}/${split_lower}.txt" || { echo "Error: download failed"; exit 1; }
            else
                echo "Error: neither curl nor wget found"; exit 1
            fi
        fi
    done

    for split in "${SPLITS[@]}"; do
        echo "Generating manifest for ${split}"
        "$PY" "$GEN_MAN_PY" \
            --txt "${MANIFEST_DIR}/${split}.txt" \
            --json-dir "${OUTPUT_ROOT}/${split}" \
            --data-root "$DATA_ROOT" \
            --out-csv "${MANIFEST_DIR}/${split}.csv" \
            --split "$split" \
            --workers "$WORKERS"
    done
fi

# ── Stage 4: Normalize references ──
if [[ $START_STAGE -le 4 ]] && [[ $STOP_STAGE -ge 4 ]]; then
    NORMALIZE_REF_PY="${PROJ_ROOT}/utils/normalize_ref.py"
    [[ -f "$NORMALIZE_REF_PY" ]] || { echo "Error: $NORMALIZE_REF_PY not found"; exit 1; }
    for split in "${SPLITS[@]}"; do
        csv_file="${MANIFEST_DIR}/${split}.csv"
        [[ ! -f "$csv_file" ]] && echo "Warning: $csv_file not found, skipping" && continue
        echo "Normalizing references for ${split}"
        "$PY" "$NORMALIZE_REF_PY" \
            --csv "$csv_file" \
            --ref-col "text" \
            --out-csv "$csv_file"
    done
fi

echo "Done."
