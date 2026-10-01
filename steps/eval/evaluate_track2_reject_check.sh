#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Standalone Track 2 rejection check helper
# ============================================================================
# Purpose: check the two Track 2 rejection rules without the full pipeline:
#   1. early first-word emission rate (from partial results JSON)
#   2. Pass 1 (predict.csv) / Pass 2 (partial results JSON) final-text consistency
#
# Usage:
#   bash ./steps/eval/evaluate_track2_reject_check.sh --partial-json JSON \
#       --manifest-csv CSV --predict-csv CSV [--mfa-col COL] [--hyp-col COL] \
#       [--early-emission-threshold T] [--out-json JSON]
#
# Notes:
# - --partial-json, --manifest-csv and --predict-csv are required.
# - --manifest-csv must have an 'id' column and the MFA start-time column
#   (default: mfa_speech_start), i.e. the streaming manifest (<split>_streaming.csv).
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PARTIAL_JSON=""
MANIFEST_CSV=""
PREDICT_CSV=""
MFA_COL="mfa_speech_start"
HYP_COL="raw_hypos"
EARLY_EMISSION_THRESHOLD="0.05"
OUT_JSON=""
REJECT_SCRIPT="${PROJ_ROOT}/utils/track2_reject_check.py"

while [[ $# -gt 0 ]]; do
  case $1 in
    --partial-json) PARTIAL_JSON="$2"; shift 2 ;;
    --manifest-csv) MANIFEST_CSV="$2"; shift 2 ;;
    --predict-csv) PREDICT_CSV="$2"; shift 2 ;;
    --mfa-col) MFA_COL="$2"; shift 2 ;;
    --hyp-col) HYP_COL="$2"; shift 2 ;;
    --early-emission-threshold) EARLY_EMISSION_THRESHOLD="$2"; shift 2 ;;
    --out-json) OUT_JSON="$2"; shift 2 ;;
    --reject-script) REJECT_SCRIPT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

[[ -z "${PARTIAL_JSON}" ]] && { echo "Error: --partial-json is required"; exit 1; }
[[ -z "${MANIFEST_CSV}" ]] && {
  echo "Error: --manifest-csv is required (needs 'id' and the MFA start-time column, --mfa-col)."
  exit 1
}
[[ -z "${PREDICT_CSV}" ]] && { echo "Error: --predict-csv is required (Pass 1 <split>.predict.csv)"; exit 1; }

CMD=(python3 "${REJECT_SCRIPT}" --partial-json "${PARTIAL_JSON}" --manifest-csv "${MANIFEST_CSV}"
     --predict-csv "${PREDICT_CSV}" --mfa-col "${MFA_COL}" --hyp-col "${HYP_COL}"
     --early-emission-threshold "${EARLY_EMISSION_THRESHOLD}")
if [[ -n "${OUT_JSON}" ]]; then
  CMD+=(--out-json "${OUT_JSON}")
fi

"${CMD[@]}"
