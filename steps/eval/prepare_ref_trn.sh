#!/usr/bin/env bash
set -euo pipefail
# Export pre-normalized ref columns from manifest CSV to .trn files (one-time).
# Usage: ./prepare_ref_trn.sh PROJ_ROOT --split SPLIT --csv CSV --ref1-col COL --ref2-col COL --out-dir DIR

# ── Positional args ──
PROJ_ROOT="${1:?Error: PROJ_ROOT is required (arg 1)}"; shift

# ── Defaults ──
SPLIT=""; CSV=""; REF1_COL=""; REF2_COL=""; OUT_DIR=""

# ── Parse ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --split)    SPLIT="$2";    shift 2 ;;
        --csv)      CSV="$2";      shift 2 ;;
        --ref1-col) REF1_COL="$2"; shift 2 ;;
        --ref2-col) REF2_COL="$2"; shift 2 ;;
        --out-dir)  OUT_DIR="$2";  shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# ── Validate ──
[[ -z "$SPLIT" ]]    && { echo "ERROR: --split is required";    exit 1; }
[[ -z "$CSV" ]]      && { echo "ERROR: --csv is required";      exit 1; }
[[ -z "$REF1_COL" ]] && { echo "ERROR: --ref1-col is required"; exit 1; }
[[ -z "$REF2_COL" ]] && { echo "ERROR: --ref2-col is required"; exit 1; }
[[ -z "$OUT_DIR" ]]  && { echo "ERROR: --out-dir is required";  exit 1; }
[[ ! -f "$CSV" ]]    && { echo "ERROR: CSV not found: ${CSV}";  exit 1; }

# ── Derived defaults ──
PY="python3"; command -v python3 &>/dev/null || PY="python"
mkdir -p "$OUT_DIR"
REF1="${OUT_DIR}/ref1.${SPLIT}.norm.trn"
REF2="${OUT_DIR}/ref2.${SPLIT}.norm.trn"

echo "=== Preparing reference .trn files ==="
echo "  Split:    ${SPLIT}"
echo "  CSV:      ${CSV}"
echo "  ref1-col: ${REF1_COL} -> ${REF1}"
echo "  ref2-col: ${REF2_COL} -> ${REF2}"

# ── Run ──
"$PY" - "$CSV" "$REF1_COL" "$REF2_COL" "$REF1" "$REF2" <<'PYEOF'
import csv, sys
csv_path, ref1_col, ref2_col, ref1_path, ref2_path = sys.argv[1:6]
with open(csv_path, "r", encoding="utf-8") as f_csv, \
     open(ref1_path, "w", encoding="utf-8") as f_ref1, \
     open(ref2_path, "w", encoding="utf-8") as f_ref2:
    reader = csv.DictReader(f_csv)
    assert ref1_col in reader.fieldnames, f"'{ref1_col}' not in {reader.fieldnames}"
    assert ref2_col in reader.fieldnames, f"'{ref2_col}' not in {reader.fieldnames}"
    n = 0
    for idx, row in enumerate(reader, start=1):
        uid = f"utt{idx:06d}"
        f_ref1.write(f"{row[ref1_col]} ({uid})\n")
        f_ref2.write(f"{row[ref2_col]} ({uid})\n")
        n += 1
print(f"  Wrote {n} utterances")
PYEOF

echo "=== Done ==="
