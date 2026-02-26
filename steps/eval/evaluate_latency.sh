#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Standalone latency evaluation helper
# ============================================================================
# Purpose: compute TTFT/TTLT from partial results JSON without full pipeline.
#
# Usage:
#   bash ./steps/eval/evaluate_latency.sh --partial-json JSON --manifest-csv CSV
#                                         [--mfa-col COL] [--out-json JSON]
#
# Notes:
# - --partial-json is required.
# - --manifest-csv is required and should be a custom CSV with:
#     1) `id` column
#     2) your MFA start-time column (default name: `mfa_speech_start`)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PARTIAL_JSON=""
MANIFEST_CSV=""
OUT_JSON=""
MFA_COL="mfa_speech_start"
LATENCY_SCRIPT="${PROJ_ROOT}/utils/compute_latency.py"

while [[ $# -gt 0 ]]; do
  case $1 in
    --partial-json) PARTIAL_JSON="$2"; shift 2 ;;
    --manifest-csv) MANIFEST_CSV="$2"; shift 2 ;;
    --out-json) OUT_JSON="$2"; shift 2 ;;
    --mfa-col) MFA_COL="$2"; shift 2 ;;
    --latency-script) LATENCY_SCRIPT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

[[ -z "${PARTIAL_JSON}" ]] && { echo "Error: --partial-json is required"; exit 1; }
[[ -z "${MANIFEST_CSV}" ]] && {
  echo "Error: --manifest-csv is required."
  echo "       Please provide a special CSV with 'id' and your MFA start-time column (use --mfa-col)."
  exit 1
}

CMD=(python3 "${LATENCY_SCRIPT}" --partial-json "${PARTIAL_JSON}")
echo "[latency] Using manifest CSV: ${MANIFEST_CSV}"
CMD+=(--manifest-csv "${MANIFEST_CSV}" --mfa-col "${MFA_COL}")
if [[ -n "${OUT_JSON}" ]]; then
  CMD+=(--out-json "${OUT_JSON}")
fi

"${CMD[@]}"


