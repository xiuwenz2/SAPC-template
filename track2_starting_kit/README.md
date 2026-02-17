# SAPC2 Track 2 — Streaming ASR Starting Kit

## Submission Interface

Your submission **must** contain a `model.py` with the following class:

```python
import numpy as np

class Model:
    def __init__(self):
        """Load and initialize your streaming ASR model here. Called once."""
        pass

    def set_partial_callback(self, callback) -> None:
        """Register a callback for partial results: callback(text: str).
        Called once per evaluation pass."""
        self._partial_callback = callback

    def reset(self) -> None:
        """Reset streaming state for a new audio file. Called once per file."""
        pass

    def accept_chunk(self, audio_chunk: np.ndarray) -> str:
        """Accept an audio chunk (float32, 16kHz, mono) and return
        the current partial transcription."""
        return "partial transcription"

    def input_finished(self) -> str:
        """Signal that all audio has been sent. Process remaining features
        and return the final transcription."""
        return "final transcription"
```

### Method Details

| Method | Called | Purpose |
|---|---|---|
| `__init__()` | Once at startup | Load model weights, tokenizer, etc. |
| `set_partial_callback(fn)` | Once per evaluation pass | Register a callback that receives partial transcription text |
| `reset()` | Once per audio file | Reset internal streaming state |
| `accept_chunk(chunk)` | Many times per file | Feed 100ms audio chunk (1600 samples at 16kHz), return partial result |
| `input_finished()` | Once per file | Signal end of audio, return final transcription |

### How Ingestion Works

The ingestion program evaluates each audio file in **two passes**:

1. **Pass 1 — Batch (accuracy)**: single-thread, no delay, feeds all chunks as fast as possible. `set_partial_callback` is set to a no-op.
2. **Pass 2 — Streaming (latency)**: two-thread real-time simulation. The **Audio Sender thread** sends 100ms chunks at real-time pace; the **Decoder thread** calls your model's `accept_chunk()` / `input_finished()` and collects partial results via the callback.

All model methods are called **from the Decoder thread only** — your model does **not** need to handle thread safety.

## Baseline Examples

| Folder | Model | Framework |
|---|---|---|
| `streaming_zipformer/` | Streaming Zipformer-Transducer | icefall |

## How to Submit

1. Choose a baseline or build your own streaming model.
2. Implement the 5-method interface in `model.py`.
3. Package into a zip:

```
submission.zip
├── model.py              # Required (5-method streaming interface)
├── setup.sh              # Recommended (environment setup script)
└── ...                   # Other supporting files (model weights, etc.)
```

4. Upload the zip on the competition page.

## Environment

- Docker image: `pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime`
- Pre-installed: **PyTorch 2.5.0+cu124**, torchaudio, torchvision
- GPU: CUDA-enabled GPU available (CUDA 12.4)
- Time limit: 21600 seconds per submission
- If a `setup.sh` is provided, it runs **before** your model is loaded. Use it to install system packages and Python dependencies.
- If a `requirements.txt` is provided, dependencies are auto-installed via `pip install -r requirements.txt` after `setup.sh`.
- **Tip**: For NeMo-based models, we recommend using `setup.sh` to create a clean virtual environment and install dependencies there, to avoid CUDA/numpy conflicts with the base conda environment.

## Notes

- The `Model` class name must be exactly `Model`.
- `set_partial_callback()` receives a callable `fn(text: str)`. Call it inside `accept_chunk()` to report partial results for latency evaluation.
- `accept_chunk()` receives a `np.ndarray` (float32, 16kHz, mono) and must return a string.
- `input_finished()` must return the final transcription string.
- Do **not** hardcode dataset file paths. Audio is sent to your model chunk by chunk.
