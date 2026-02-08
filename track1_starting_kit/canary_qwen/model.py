#!/usr/bin/env python3
"""
Baseline: NVIDIA Canary-Qwen 2.5B (NeMo SALM).
Participants must implement a Model class with a predict(wav_path) method.
"""
import torch
from nemo.collections.speechlm2.models import SALM


class Model:
    """ASR Model using NeMo Canary-Qwen-2.5B."""

    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading canary-qwen-2.5b on {device}")

        self.model = SALM.from_pretrained("nvidia/canary-qwen-2.5b")
        self.model = self.model.to(device)
        self.model.eval()

        # Use beam search with beam_size=5
        self.model.llm.generation_config.num_beams = 5

    def predict(self, wav_path: str, max_new_tokens: int = 512) -> str:
        """
        Transcribe a single wav file.

        Args:
            wav_path: path to the wav file.
            max_new_tokens: max tokens to generate per utterance.

        Returns:
            Transcribed text string.
        """
        prompts = [
            [
                {
                    "role": "user",
                    "content": f"Transcribe the following: {self.model.audio_locator_tag}",
                    "audio": [wav_path],
                }
            ]
        ]

        with torch.inference_mode():
            answer_ids = self.model.generate(
                prompts=prompts, max_new_tokens=max_new_tokens
            )

        text = self.model.tokenizer.ids_to_text(answer_ids[0].cpu())
        return text.strip()

