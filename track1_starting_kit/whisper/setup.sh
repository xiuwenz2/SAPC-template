#!/bin/bash
set -e

echo "=== Whisper: installing Python packages ==="
pip install --no-cache-dir \
    "huggingface_hub>=0.20" \
    "filelock>=3.12" \
    "faster-whisper>=1.0.0" \
    "tqdm>=4.65.0"

echo "=== Whisper: verifying installation ==="
python3 -c "
import torch
from faster_whisper import WhisperModel
print('Torch version:', torch.__version__)
print('faster-whisper import: OK')
"

echo "=== Whisper: setup complete ==="

