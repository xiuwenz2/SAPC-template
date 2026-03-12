#!/usr/bin/env bash
set -euo pipefail
# Build a latency-evaluation subset from input manifests.
# Usage: ./generate_streaming_subset.sh DATA_ROOT PROJ_ROOT WEBRTCVAD_ENV MFA_ENV [OPTIONS]
#   Stages: 1=duration, 2=VAD, 3=MFA, 4=FA/VAD, 5=tail-gap, 6=speaker1-subset, 7=stats

# ── Positional args ──
DATA_ROOT="${1:?Error: DATA_ROOT is required (arg 1)}"; shift
PROJ_ROOT="${1:?Error: PROJ_ROOT is required (arg 2)}"; shift
WEBRTCVAD_ENV="${1:?Error: WEBRTCVAD_ENV is required (arg 3)}"; shift
MFA_ENV="${1:?Error: MFA_ENV is required (arg 4)}"; shift

# ── Defaults ──
MANIFEST_DIR="${DATA_ROOT}/manifest"
START_STAGE=1; STOP_STAGE=7
MIN_DUR=3
MAX_DUR=30
WORKERS=64
SPLITS=("Train" "Dev")
TMP_DIR="${MANIFEST_DIR}/tmp"
STREAMING_UTIL_DIR="${PROJ_ROOT}/utils/streaming_subset"

# ── Parse ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --start_stage) START_STAGE="$2"; shift 2 ;;
        --stop_stage)  STOP_STAGE="$2";  shift 2 ;;
        --workers)     WORKERS="$2";     shift 2 ;;
        --splits)
            SPLITS=(); shift
            while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do SPLITS+=("$1"); shift; done ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# ── Validate ──
[[ "$START_STAGE" =~ ^[1-7]$ ]] && [[ "$STOP_STAGE" =~ ^[1-7]$ ]] && [[ $START_STAGE -le $STOP_STAGE ]] \
    || { echo "Error: stages must be 1-7, start <= stop"; exit 1; }
[[ ${#SPLITS[@]} -gt 0 ]] || { echo "Error: --splits is required"; exit 1; }

# ── Run ──
echo "Splits: ${SPLITS[*]}, Stages: ${START_STAGE}-${STOP_STAGE}, Workers: ${WORKERS}"
mkdir -p "$TMP_DIR"

# ── Stage 1: Duration filtering ──
if [[ $START_STAGE -le 1 ]] && [[ $STOP_STAGE -ge 1 ]]; then
    echo "Stage 1: duration filtering (${MIN_DUR}s-${MAX_DUR}s)"
    for split in "${SPLITS[@]}"; do
        csv="${MANIFEST_DIR}/${split}.csv"
        out="${TMP_DIR}/${split}.csv"
        head -1 "$csv" > "$out"
        awk -F',' -v min="$MIN_DUR" -v max="$MAX_DUR" \
            'NR>1 { d = $5 + 0; if (d >= min && d <= max) print }' "$csv" >> "$out"
        orig=$(awk 'END{print NR-1}' "$csv")
        filt=$(awk 'END{print NR-1}' "$out")
        ratio=$(awk -v o="$orig" -v f="$filt" 'BEGIN{ if (o>0) printf "%.1f", f*100/o; else printf "0.0" }')
        echo "  ${split}: ${orig} -> ${filt} (${ratio}%)"
    done
fi

# ── Stage 2: WebRTC VAD ──
if [[ $START_STAGE -le 2 ]] && [[ $STOP_STAGE -ge 2 ]]; then
    echo "Stage 2: WebRTC VAD"
    eval "$(conda shell.bash hook)"
    conda activate "$WEBRTCVAD_ENV"
    for split in "${SPLITS[@]}"; do
        python "${STREAMING_UTIL_DIR}/run_vad_webrtcvad.py" \
            --input-csv "${TMP_DIR}/${split}.csv" \
            --audio-root "$DATA_ROOT" \
            --output-csv "${TMP_DIR}/${split}_vad.csv" \
            --aggressiveness 3 \
            --frame-duration 30 \
            --num-workers "$WORKERS"
    done
    conda deactivate
fi

# ── Stage 3: MFA ──
if [[ $START_STAGE -le 3 ]] && [[ $STOP_STAGE -ge 3 ]]; then
    echo "Stage 3: MFA"
    eval "$(conda shell.bash hook)"
    conda activate "$MFA_ENV"
    for split in "${SPLITS[@]}"; do
        python "${STREAMING_UTIL_DIR}/run_mfa.py" \
            --input-csv "${TMP_DIR}/${split}.csv" \
            --audio-root "$DATA_ROOT" \
            --output-csv "${TMP_DIR}/${split}_mfa.csv" \
            --num-workers "$WORKERS"
    done
    conda deactivate
fi

# ── Stage 4: FA/VAD filtering ──
if [[ $START_STAGE -le 4 ]] && [[ $STOP_STAGE -ge 4 ]]; then
    echo "Stage 4: FA/VAD filtering (<=0.1s)"
    for split in "${SPLITS[@]}"; do
        python "${STREAMING_UTIL_DIR}/run_filter_by_alignment_match.py" \
            --fa-csv "${TMP_DIR}/${split}_mfa.csv" \
            --vad-csv "${TMP_DIR}/${split}_vad.csv" \
            --base-csv "${TMP_DIR}/${split}.csv" \
            --ranked-csv "${TMP_DIR}/${split}_fa_vad_ranked.csv" \
            --filtered-csv "${TMP_DIR}/${split}_fa_vad_filtered.csv" \
            --threshold 0.1
    done
fi

# ── Stage 5: Tail-gap filtering ──
if [[ $START_STAGE -le 5 ]] && [[ $STOP_STAGE -ge 5 ]]; then
    echo "Stage 5: tail-gap filtering (0.5s-1.5s)"
    for split in "${SPLITS[@]}"; do
        python "${STREAMING_UTIL_DIR}/run_tail_gap_stats.py" \
            --input-filtered-csv "${TMP_DIR}/${split}_fa_vad_filtered.csv" \
            --vad-csv "${TMP_DIR}/${split}_vad.csv" \
            --output-csv "${TMP_DIR}/${split}_tail_gap_ranked.csv" \
            --min-gap 0.5 \
            --max-gap 1.5 \
            --output-filtered-csv "${TMP_DIR}/${split}_tail_gap_filtered.csv"
    done
fi

# ── Stage 6: One sample per speaker ──
if [[ $START_STAGE -le 6 ]] && [[ $STOP_STAGE -ge 6 ]]; then
    echo "Stage 6: one sample per speaker (seed=42)"
    for split in "${SPLITS[@]}"; do
        python "${STREAMING_UTIL_DIR}/run_sample_one_per_speaker.py" \
            --input-csv "${TMP_DIR}/${split}_tail_gap_filtered.csv" \
            --output-csv "${MANIFEST_DIR}/${split}_streaming.csv" \
            --seed 42 \
            --order-csv "${TMP_DIR}/${split}.csv" \
            --mfa-csv "${TMP_DIR}/${split}_mfa.csv" \
            --vad-csv "${TMP_DIR}/${split}_vad.csv"
    done
fi

# ── Stage 7: Duration stats ──
if [[ $START_STAGE -le 7 ]] && [[ $STOP_STAGE -ge 7 ]]; then
    echo "Stage 7: duration stats"
    for split in "${SPLITS[@]}"; do
        python "${STREAMING_UTIL_DIR}/run_duration_stats.py" \
            --input-csv "${MANIFEST_DIR}/${split}_streaming.csv" \
            --output-csv "${TMP_DIR}/${split}_streaming_duration_bins.csv"
    done
fi

echo "Done."
