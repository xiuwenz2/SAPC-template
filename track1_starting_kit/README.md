# SAPC2 Starting Kit

## Submission Interface

Your submission **must** contain a `model.py` with the following class:

```python
class Model:
    def __init__(self):
        # Load and initialize your ASR model here.
        pass

    def predict(self, wav_path: str) -> str:
        # Transcribe a single wav file and return the text.
        return "transcribed text"
```

## Baseline Examples

We provide three baseline examples. Pick one as your starting point:

| Folder | Model | Framework |
|---|---|---|
| `whisper/` | Whisper large-v2 | faster-whisper |
| `parakeet/` | Parakeet TDT 0.6B v2 | NeMo |
| `canary_qwen/` | Canary-Qwen 2.5B | NeMo |

## How to Submit

1. Choose a baseline (or build your own).
2. Modify `model.py` as needed.
3. Package into a zip:

```
submission.zip
├── model.py              # Required
├── setup.sh              # Recommended (environment setup script)
└── ...                   # Other supporting files (optional)
```

4. Upload the zip on the competition page.

## Environment

- Docker image: `pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime`
- Pre-installed: **PyTorch 2.5.0+cu124**, torchaudio, torchvision
- GPU: CUDA-enabled GPU available (CUDA 12.4)
- Time limit: 15000 seconds per submission
- If a `setup.sh` is provided, it runs **before** your model is loaded. Use it to install system packages and Python dependencies.
- If a `requirements.txt` is provided, dependencies are auto-installed via `pip install -r requirements.txt` after `setup.sh`.
- **Tip**: For NeMo-based models (parakeet, canary_qwen), we recommend using `setup.sh` to create a clean virtual environment and install dependencies there, to avoid CUDA/numpy conflicts with the base conda environment. See the `parakeet/` or `canary_qwen/` baselines for examples.

## Notes

- The `Model` class name must be exactly `Model`.
- `predict()` receives an absolute path to a `.wav` file and must return a string.
- Do **not** hardcode file paths; use only the `wav_path` argument passed to `predict()`.
