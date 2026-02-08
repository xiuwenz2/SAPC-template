#!/usr/bin/env bash
set -euo pipefail
# Set up conda environment and install dependencies.
# Usage: ./env.sh CONDA_ENV_NAME

# ── Positional args ──
CONDA_ENV_NAME="${1:?Error: CONDA_ENV_NAME is required (arg 1)}"

# ── Defaults ──
PACKAGES=("soundfile" "librosa" "tqdm" "pandas")

# ── Run ──
echo "Setting up conda environment: ${CONDA_ENV_NAME}"

if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
    echo "Environment already exists, activating..."
    conda init
    conda activate "$CONDA_ENV_NAME"
else
    echo "Creating new environment..."
    conda create --name "$CONDA_ENV_NAME" python=3.11 -y
    conda init
    conda activate "$CONDA_ENV_NAME"
    pip install "${PACKAGES[@]}"
fi

echo "Done."
