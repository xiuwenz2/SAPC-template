#!/bin/bash
set -e

echo "=== Parakeet: installing system dependencies ==="
apt-get update -qq
apt-get install -y -qq libsndfile1 ffmpeg > /dev/null 2>&1

# ── Create a clean venv to bypass conda's broken CUDA / numpy .so files ──
# The conda env may have PyTorch built for a different CUDA arch, causing
# "no kernel image is available for execution on the device".
# A fresh venv with the correct torch build avoids all conflicts.
echo "=== Parakeet: creating clean venv ==="
python3 -m venv /opt/parakeet_venv
/opt/parakeet_venv/bin/pip install --upgrade pip -q

echo "=== Parakeet: installing packages into venv ==="
/opt/parakeet_venv/bin/pip install --no-cache-dir \
    "nemo_toolkit[asr]==2.5.3" \
    "numpy>=1.26,<2.1" \
    "matplotlib>=3.8" \
    "huggingface_hub>=0.24" \
    "filelock>=3.12" \
    "tqdm>=4.65.0" \
    torch torchaudio torchvision

echo "=== Parakeet: verifying installation ==="
/opt/parakeet_venv/bin/python3 -c "
import numpy, torch
import nemo.collections.asr as nemo_asr
print('NumPy version:', numpy.__version__)
print('Torch version:', torch.__version__)
print('NeMo import: OK')
"

echo "=== Parakeet: setup complete ==="

