#!/bin/bash
# =====================================================================
# Streaming Zipformer — Environment Setup
#
# This script prepares everything needed to run the model:
#   Stage 1: Detect your Python & PyTorch versions
#   Stage 2: Install required Python packages
#   Stage 3: Download pre-trained model weights
#
# Run this once before using the model.
# =====================================================================
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

# =============================================================
# Stage 1: Detect environment
# =============================================================
echo "=== Stage 1: Detect environment ==="
# We need PyTorch and Python version info to find the correct
# pre-built wheels for k2 and kaldifeat.
TORCH_VER=$(python3 -c "import torch; print(torch.__version__.split('+')[0])")
PY_TAG="cp$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")"
echo "PyTorch version: $TORCH_VER | Python tag: $PY_TAG"

# Direct wheel URLs for torch2.5.0 + cp311 + linux x86_64
K2_WHEEL="https://huggingface.co/csukuangfj/k2/resolve/main/cpu/1.24.4.dev20250307/linux-x64/k2-1.24.4.dev20250714+cpu.torch2.5.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"
KALDIFEAT_WHEEL="https://huggingface.co/csukuangfj/kaldifeat/resolve/main/cpu/1.25.5.dev20250307/linux-x64/kaldifeat-1.25.5.dev20250630+cpu.torch2.5.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"

# =============================================================
# Stage 2: Install packages
# =============================================================
echo "=== Stage 2: Install packages ==="

# Basic dependencies
pip install -q numpy sentencepiece tqdm huggingface_hub graphviz lhotse omegaconf

# k2: finite-state transducer library (used by icefall for decoding)
pip install --no-deps "$K2_WHEEL"

# kaldifeat: audio feature extraction (Fbank/MFCC, Kaldi-compatible)
pip install --no-deps "$KALDIFEAT_WHEEL"

# icefall: speech recognition toolkit built on k2 + PyTorch
git clone --depth 1 https://github.com/k2-fsa/icefall.git "$DIR/icefall"
cd "$DIR/icefall" && pip install -e . && cd "$DIR"

# =============================================================
# Stage 3: Download model weights
# =============================================================
echo "=== Stage 3: Download model weights ==="
# Download the pre-trained checkpoint and BPE tokenizer model
# from Hugging Face into the weights/ directory.
python3 -c "
from huggingface_hub import hf_hub_download
import os
repo = 'Zengwei/icefall-asr-librispeech-streaming-zipformer-2023-05-17'
wd = '$DIR/weights'
os.makedirs(wd + '/exp', exist_ok=True)
os.makedirs(wd + '/data/lang_bpe_500', exist_ok=True)
for f in ['exp/epoch-30.pt', 'data/lang_bpe_500/bpe.model']:
    hf_hub_download(repo_id=repo, filename=f, local_dir=wd)
"

echo "=== setup.sh complete ==="
