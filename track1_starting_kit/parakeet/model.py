#!/usr/bin/env python3
"""
Baseline: NVIDIA Parakeet TDT 0.6B v2 (NeMo).
Participants must implement a Model class with a predict(wav_path) method.
"""
import torch
import nemo.collections.asr as nemo_asr


class Model:
    """ASR Model using NeMo Parakeet."""

    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading parakeet-tdt-0.6b-v2 on {device}")

        self.model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v2"
        )
        self.model = self.model.to(device)

        # Switch to beam search decoding (beam_size=5)
        cfg = self.model.cfg
        cfg.decoding.strategy = "beam"
        cfg.decoding.beam.beam_size = 5
        cfg.decoding.beam.return_best_hypothesis = True
        if hasattr(self.model, "change_decoding_strategy"):
            self.model.change_decoding_strategy(cfg.decoding)

    def predict(self, wav_path: str) -> str:
        """
        Transcribe a single wav file.

        Args:
            wav_path: path to the wav file.

        Returns:
            Transcribed text string.
        """
        outputs = self.model.transcribe([wav_path], verbose=False)
        if not outputs:
            return ""
        first = outputs[0]
        text = first if isinstance(first, str) else getattr(first, "text", "") or ""
        return text.strip()

