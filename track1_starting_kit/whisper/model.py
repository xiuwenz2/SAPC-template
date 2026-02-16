#!/usr/bin/env python3
"""
Baseline: Whisper large-v2 (faster-whisper).
Participants must implement a Model class with a predict(wav_path) method.
"""
import torch
from faster_whisper import WhisperModel


class Model:
    """ASR Model using faster-whisper."""

    def __init__(self):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available — this track requires GPU.")
        device = "cuda"
        compute_type = "float16"
        print(f"Loading whisper large-v2 on {device} ({compute_type})")

        self.model = WhisperModel("large-v2", device=device, compute_type=compute_type)

    def predict(self, wav_path: str) -> str:
        """
        Transcribe a single wav file.

        Args:
            wav_path: path to the wav file.

        Returns:
            Transcribed text string.
        """
        segments, _ = self.model.transcribe(wav_path, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()
