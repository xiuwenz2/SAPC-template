#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Standalone stable sentence-prefix match helper
# ============================================================================
# Purpose: compute stable_sentence_prefix_match_rate from
#          partial results JSON without the full pipeline.
#
# Usage:
#   bash ./steps/eval/evaluate_stable_sentence_prefix_match.sh --partial-json JSON \
#       --manifest-csv CSV [--ref-col COL] [--out-json JSON]
#
# Notes:
# - --partial-json is required.
# - --manifest-csv is required and must have an 'id' column and the
#   reference text column (default: norm_text_without_disfluency).
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PARTIAL_JSON=""
MANIFEST_CSV=""
REF_COL="norm_text_without_disfluency"
OUT_JSON=""
STABLE_PREFIX_SCRIPT="${PROJ_ROOT}/utils/stable_sentence_prefix_match.py"

while [[ $# -gt 0 ]]; do
  case $1 in
    --partial-json) PARTIAL_JSON="$2"; shift 2 ;;
    --manifest-csv) MANIFEST_CSV="$2"; shift 2 ;;
    --ref-col) REF_COL="$2"; shift 2 ;;
    --out-json) OUT_JSON="$2"; shift 2 ;;
    --stable-prefix-script) STABLE_PREFIX_SCRIPT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

[[ -z "${PARTIAL_JSON}" ]] && { echo "Error: --partial-json is required"; exit 1; }
[[ -z "${MANIFEST_CSV}" ]] && {
  echo "Error: --manifest-csv is required (needs 'id' and the reference column, --ref-col)."
  exit 1
}

CMD=(python3 "${STABLE_PREFIX_SCRIPT}" --partial-json "${PARTIAL_JSON}" --manifest-csv "${MANIFEST_CSV}" --ref-col "${REF_COL}")
if [[ -n "${OUT_JSON}" ]]; then
  CMD+=(--out-json "${OUT_JSON}")
fi

"${CMD[@]}"
