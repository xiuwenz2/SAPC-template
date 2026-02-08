#!/usr/bin/env bash
set -euo pipefail
# Evaluate ASR predictions (thin wrapper around utils/evaluate.py).
# Usage: ./evaluate.sh PROJ_ROOT DATA_ROOT --split SPLIT --hyp-csv CSV [OPTIONS]

# ── Positional args ──
PROJ_ROOT="${1:?Error: PROJ_ROOT is required (arg 1)}"; shift
DATA_ROOT="${1:?Error: DATA_ROOT is required (arg 2)}"; shift

# ── Defaults ──
SPLIT=""; HYP_CSV=""; HYP_COL="raw_hypos"
MANIFEST_CSV=""; REF_DIR=""; OUT_JSON=""

# ── Parse ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --split)        SPLIT="$2";        shift 2 ;;
        --hyp-csv)      HYP_CSV="$2";      shift 2 ;;
        --hyp-col)      HYP_COL="$2";      shift 2 ;;
        --manifest-csv) MANIFEST_CSV="$2";  shift 2 ;;
        --ref-dir)      REF_DIR="$2";       shift 2 ;;
        --out-json)     OUT_JSON="$2";      shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# ── Validate ──
[[ -z "$SPLIT" ]]   && { echo "ERROR: --split is required";   exit 1; }
[[ -z "$HYP_CSV" ]] && { echo "ERROR: --hyp-csv is required"; exit 1; }
[[ -z "$REF_DIR" ]] && { echo "ERROR: --ref-dir is required"; exit 1; }

# ── Derived defaults ──
PY="python3"; command -v python3 &>/dev/null || PY="python"
[[ -z "$MANIFEST_CSV" ]] && MANIFEST_CSV="${REF_DIR}/${SPLIT}.csv"
EVAL_DIR="${DATA_ROOT}/eval"

# ── Run ──
CMD=("$PY" "${PROJ_ROOT}/utils/evaluate.py"
    --split        "$SPLIT"
    --hyp-csv      "$HYP_CSV"
    --hyp-col      "$HYP_COL"
    --manifest-csv "$MANIFEST_CSV"
    --ref-dir      "$REF_DIR"
    --eval-dir     "$EVAL_DIR"
)
[[ -n "$OUT_JSON" ]] && CMD+=(--out-json "$OUT_JSON")
"${CMD[@]}"
