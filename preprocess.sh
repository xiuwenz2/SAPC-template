#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# SAP Challenge Main Pipeline Script
# ============================================================================
# Purpose: Run the complete data processing pipeline
# 
# This script runs the following steps in order:
#   1. Environment setup (steps/env.sh)
#   2. Data extraction (steps/unzip.sh)
#   3. Data preprocessing (steps/preprocess.sh)
#   4. Optional streaming subset generation for latency tests (steps/generate_streaming_subset.sh)
#
# Usage:
#   ./preprocess.sh [--start_stage STAGE] [--stop_stage STAGE] [--splits SPLIT1 SPLIT2 ...]
#   
#   Arguments:
#     --start_stage  : Start from this stage (1-4, default: 1)
#     --stop_stage   : Stop at this stage (1-4, default: 3)
#     --splits       : Dataset splits to process (default: Train Dev)
#
#   Default values (modify in script):
#     CONDA_ENV_NAME : Conda environment name
#     DATA_ROOT       : Data root directory
#     PROJ_ROOT       : Project root directory
#     WEBRTCVAD_ENV   : Conda env for WebRTC VAD (used in stage 4)
#     MFA_ENV         : Conda env for MFA (used in stage 4)
#     SPLITS          : Dataset splits to process
#     WORKERS         : Number of parallel workers
#
#   Stages:
#     1: Environment setup
#     2: Data extraction
#     3: Data preprocessing
#     4: Optional streaming subset generation for latency tests
# ============================================================================

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEPS_DIR="${SCRIPT_DIR}/steps"

# Default values
CONDA_ENV_NAME="sapc2"                                  ### TODO: change to your conda env name
DATA_ROOT="/path/to/data"                               ### TODO: change to your data root
PROJ_ROOT="/path/to/SAPC-template"                      ### TODO: change to your project root
SPLITS=("Train" "Dev")
WORKERS=$(n=$( (command -v nproc >/dev/null 2>&1 && nproc) || echo 4); echo $((n > 108 ? 108 : n)))
START_STAGE=1
STOP_STAGE=3
WEBRTCVAD_ENV="/path/to/webrtcvad_env"    ### TODO: if use stage 4, change to your VAD env
MFA_ENV="/path/to/mfa_env"                ### TODO: if use stage 4, change to your MFA env

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --start_stage) START_STAGE="$2"; shift 2 ;;
    --stop_stage) STOP_STAGE="$2"; shift 2 ;;
    --splits)
      SPLITS=()
      shift
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do
        SPLITS+=("$1")
        shift
      done
      ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# Validate stages
if [[ ! "$START_STAGE" =~ ^[1234]$ ]] || [[ ! "$STOP_STAGE" =~ ^[1234]$ ]] || [[ $START_STAGE -gt $STOP_STAGE ]]; then
  echo "Error: Invalid stage parameters (must be 1-4, start <= stop)"
  exit 1
fi

echo "Pipeline stages: ${START_STAGE}-${STOP_STAGE}"

# Step 1: Environment setup
if [[ $START_STAGE -le 1 ]] && [[ $STOP_STAGE -ge 1 ]]; then
  bash "${STEPS_DIR}/preprocess/env.sh" "$CONDA_ENV_NAME"
fi

# Step 2: Data extraction
if [[ $START_STAGE -le 2 ]] && [[ $STOP_STAGE -ge 2 ]]; then
  bash "${STEPS_DIR}/preprocess/unzip.sh" "$DATA_ROOT" --splits "${SPLITS[@]}"
fi

# Step 3: Data preprocessing
if [[ $START_STAGE -le 3 ]] && [[ $STOP_STAGE -ge 3 ]]; then
  bash "${STEPS_DIR}/preprocess/preprocess.sh" "$CONDA_ENV_NAME" "$DATA_ROOT" "$PROJ_ROOT" --splits "${SPLITS[@]}" --workers "$WORKERS"
fi

# Step 4: Optional streaming subset generation for latency tests
if [[ $START_STAGE -le 4 ]] && [[ $STOP_STAGE -ge 4 ]]; then
  bash "${STEPS_DIR}/preprocess/generate_streaming_subset.sh" "$DATA_ROOT" "$PROJ_ROOT" "$WEBRTCVAD_ENV" "$MFA_ENV" --splits "${SPLITS[@]}" --workers "$WORKERS"
fi

echo "Done."
