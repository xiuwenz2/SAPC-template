#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# SAP Challenge Evaluation Pipeline Script
# ============================================================================
# Purpose: Run the complete ASR evaluation pipeline
#
# This script runs the following steps in order:
#   0. Install SCTK (sclite) if not already installed      [one-time]
#   1. Prepare reference .trn files from CSV columns        [one-time]
#   2. Evaluate hypothesis against refs (normalize hyp → sclite → metrics)
#   3. Compute latency metrics from partial results JSON (TTFT/TTFT-STABLE/TTLT)
#   4. Compute stable sentence-prefix match rate from partial results JSON
#
# Usage:
#   ./evaluate.sh [--start_stage STAGE] [--stop_stage STAGE] [--split SPLIT]
#                 [--hyp-csv CSV] [--hyp-col COL]
#                 [--partial-json JSON] [--manifest-csv CSV]
#
#   Default values (modify in script):
#     DATA_ROOT      : Data root directory
#     PROJ_ROOT      : Project root directory
#
#   Stages:
#     0: Install SCTK (only needed once)
#     1: Prepare reference .trn files from CSV columns (only needed once per split)
#     2: Evaluate (normalize hyp → sclite → metrics)
#     3: Compute latency metrics from partial_results.json
#     4: Stable sentence-prefix match check from partial_results.json (stable_sentence_prefix_match_rate)
# ============================================================================

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEPS_DIR="${SCRIPT_DIR}/steps"

# Default values
DATA_ROOT="/path/to/data"                  ### TODO: change to your data root
PROJ_ROOT="/path/to/SAPC-template"         ### TODO: change to your project root
SCTK_DIR="/path/to/SCTK"                   ### TODO: change to your SCTK install location

SPLIT="Dev"
HYP_CSV="/path/to/hypothesis.csv"          ### TODO: change to your hypothesis CSV
HYP_COL="raw_hypos"                        # column name in hypothesis CSV containing raw transcriptions

START_STAGE=0
STOP_STAGE=2

# Optional latency stage settings (stage 3)
PARTIAL_JSON=""                           # path to <split>.partial_results.json
LATENCY_OUT_JSON=""                       # optional output json path
LATENCY_SCRIPT="${SCRIPT_DIR}/utils/compute_latency.py"   # override if needed
LATENCY_MANIFEST_CSV=""                   # required for stage 3: CSV with id + MFA start-time column
MFA_COL="mfa_speech_start"                # manifest column for force-alignment speech start

# Optional stable sentence-prefix match stage settings (stage 4)
STABLE_PREFIX_OUT_JSON=""                 # optional output json path
STABLE_PREFIX_SCRIPT="${SCRIPT_DIR}/utils/stable_sentence_prefix_match.py"   # override if needed
STABLE_PREFIX_REF_COL="norm_text_without_disfluency"                  # manifest reference column

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --start_stage)  START_STAGE="$2";  shift 2 ;;
    --stop_stage)   STOP_STAGE="$2";   shift 2 ;;
    --split)        SPLIT="$2";        shift 2 ;;
    --hyp-csv)      HYP_CSV="$2";     shift 2 ;;
    --hyp-col)      HYP_COL="$2";     shift 2 ;;
    --partial-json) PARTIAL_JSON="$2"; shift 2 ;;
    --manifest-csv) LATENCY_MANIFEST_CSV="$2"; shift 2 ;;
    --latency-out-json) LATENCY_OUT_JSON="$2"; shift 2 ;;
    --latency-script) LATENCY_SCRIPT="$2"; shift 2 ;;
    --mfa-col) MFA_COL="$2"; shift 2 ;;
    --stable-prefix-out-json) STABLE_PREFIX_OUT_JSON="$2"; shift 2 ;;
    --stable-prefix-script) STABLE_PREFIX_SCRIPT="$2"; shift 2 ;;
    --stable-prefix-ref-col) STABLE_PREFIX_REF_COL="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# Add SCTK to PATH
export PATH="${SCTK_DIR}/bin:$PATH"

# Derived paths
MANIFEST_CSV="${DATA_ROOT}/manifest/${SPLIT}.csv"
REF_DIR="${DATA_ROOT}/manifest"

# Validate stages
if [[ ! "$START_STAGE" =~ ^[0-4]$ ]] || [[ ! "$STOP_STAGE" =~ ^[0-4]$ ]] || [[ $START_STAGE -gt $STOP_STAGE ]]; then
  echo "Error: Invalid stage parameters (must be 0-4, start <= stop)"
  exit 1
fi

echo "Evaluation pipeline: stages ${START_STAGE}-${STOP_STAGE}, split=${SPLIT}"

# Step 0: Install SCTK (one-time)
if [[ $START_STAGE -le 0 ]] && [[ $STOP_STAGE -ge 0 ]]; then
  if command -v sclite &>/dev/null; then
    echo "[0] sclite already installed: $(which sclite)"
  else
    echo "[0] Installing SCTK..."
    git clone https://github.com/usnistgov/SCTK.git "${SCTK_DIR}"
    cd "${SCTK_DIR}"
    make config
    make all
    make install
    cd "${SCRIPT_DIR}"
    export PATH="${SCTK_DIR}/bin:$PATH"
    echo "[0] SCTK installed at ${SCTK_DIR}/bin"
    sclite -V || true
  fi
fi

# Step 1: Prepare reference .trn files (one-time per split)
if [[ $START_STAGE -le 1 ]] && [[ $STOP_STAGE -ge 1 ]]; then
  bash "${STEPS_DIR}/eval/prepare_ref_trn.sh" "$PROJ_ROOT" \
    --split "$SPLIT" --csv "$MANIFEST_CSV" \
    --ref1-col "norm_text_with_disfluency" --ref2-col "norm_text_without_disfluency" --out-dir "$REF_DIR"
fi

# Step 2: Evaluate
if [[ $START_STAGE -le 2 ]] && [[ $STOP_STAGE -ge 2 ]]; then
  [[ -z "${HYP_CSV}" ]] && { echo "Error: --hyp-csv is required for stage 2"; exit 1; }
  bash "${STEPS_DIR}/eval/evaluate.sh" "$PROJ_ROOT" "$DATA_ROOT" \
    --split "$SPLIT" --hyp-csv "$HYP_CSV" --hyp-col "$HYP_COL" --ref-dir "$REF_DIR" \
    --manifest-csv "$MANIFEST_CSV"
fi

# Step 3: Latency metrics from partial results json
if [[ $START_STAGE -le 3 ]] && [[ $STOP_STAGE -ge 3 ]]; then
  [[ -z "${PARTIAL_JSON}" ]] && { echo "Error: --partial-json is required for stage 3"; exit 1; }
  [[ -z "${LATENCY_MANIFEST_CSV}" ]] && {
    echo "Error: --manifest-csv is required for stage 3."
    echo "       Provide a special CSV with 'id' and your MFA start-time column (use --mfa-col)."
    exit 1
  }
  LATENCY_EVAL_SH="${STEPS_DIR}/eval/evaluate_latency.sh"

  echo "[3] Computing latency metrics via ${LATENCY_EVAL_SH}"
  LATENCY_CMD=(bash "${LATENCY_EVAL_SH}" --partial-json "${PARTIAL_JSON}" --mfa-col "${MFA_COL}")
  LATENCY_CMD+=(--manifest-csv "${LATENCY_MANIFEST_CSV}")
  if [[ -n "${LATENCY_OUT_JSON}" ]]; then
    LATENCY_CMD+=(--out-json "${LATENCY_OUT_JSON}")
  fi
  LATENCY_CMD+=(--latency-script "${LATENCY_SCRIPT}")
  "${LATENCY_CMD[@]}"
fi

# Step 4: Stable sentence-prefix match check (stable_sentence_prefix_match_rate)
if [[ $START_STAGE -le 4 ]] && [[ $STOP_STAGE -ge 4 ]]; then
  [[ -z "${PARTIAL_JSON}" ]] && { echo "Error: --partial-json is required for stage 4"; exit 1; }
  STABLE_PREFIX_EVAL_SH="${STEPS_DIR}/eval/evaluate_stable_sentence_prefix_match.sh"

  echo "[4] Computing stable sentence-prefix match rate via ${STABLE_PREFIX_EVAL_SH}"
  STABLE_PREFIX_CMD=(bash "${STABLE_PREFIX_EVAL_SH}" --partial-json "${PARTIAL_JSON}")
  STABLE_PREFIX_CMD+=(--manifest-csv "${MANIFEST_CSV}" --ref-col "${STABLE_PREFIX_REF_COL}")
  if [[ -n "${STABLE_PREFIX_OUT_JSON}" ]]; then
    STABLE_PREFIX_CMD+=(--out-json "${STABLE_PREFIX_OUT_JSON}")
  fi
  STABLE_PREFIX_CMD+=(--stable-prefix-script "${STABLE_PREFIX_SCRIPT}")
  "${STABLE_PREFIX_CMD[@]}"
fi

echo "Done."
