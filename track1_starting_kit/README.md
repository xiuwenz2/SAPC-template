# SAPC2 Starting Kit for Track 1

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
├── requirements.txt      # Recommended
└── ...                   # Other supporting files (optional)
```

4. Upload the zip on the competition page.

## Environment

- Docker image: `pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime`
- GPU: CUDA-enabled GPU available
- Time limit: 21600 seconds per submission
- Dependencies in `requirements.txt` are auto-installed before execution.

## Notes

- The `Model` class name must be exactly `Model`.
- `predict()` receives an absolute path to a `.wav` file and must return a string.
- Do **not** hardcode file paths; use only the `wav_path` argument passed to `predict()`.

