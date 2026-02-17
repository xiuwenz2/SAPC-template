#!/usr/bin/env python3
"""
Streaming Zipformer ASR Model — SAPC2 Track 2 Baseline
======================================================

This file implements a streaming (real-time) speech recognition model
using icefall's Zipformer-Transducer architecture.

How streaming ASR works (simplified):
  1. Audio arrives in small chunks (e.g. 100 ms at a time).
  2. Each chunk is converted to acoustic features (Fbank).
  3. The encoder (Zipformer) processes features chunk by chunk.
  4. The decoder (Transducer) outputs token IDs incrementally.
  5. Token IDs are decoded back to text via a BPE tokenizer.

Required interface (called by the ingestion program):
  __init__()                        — Load model weights      (called once)
  set_partial_callback(fn) -> None  — Register partial result callback (once)
  reset()             -> None       — Reset state              (once per file)
  accept_chunk(buf)   -> str        — Feed audio chunk         (many per file)
  input_finished()    -> str        — Signal end of audio      (once per file)

To change hyper-parameters, edit config.yaml (not this file).

Directory layout after running setup.sh:
  streaming_zipformer/
  ├── model.py                 ← this file
  ├── config.yaml              ← all tunable settings
  ├── setup.sh                 ← installs deps & downloads weights
  ├── icefall/                 ← icefall source (cloned by setup.sh)
  └── weights/
      ├── exp/epoch-30.pt              ← model checkpoint
      └── data/lang_bpe_500/bpe.model  ← BPE tokenizer
"""

# =====================================================================
# Section 1: Imports
# =====================================================================
import argparse
import os
import sys
from pathlib import Path
from typing import List

from omegaconf import OmegaConf
import numpy as np
import torch
import sentencepiece as spm
from kaldifeat import Fbank, FbankOptions

# =====================================================================
# Section 2: Path Setup
# =====================================================================
# All paths are relative to this file's location so the code works
# regardless of where the submission is unpacked.
_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
_ICEFALL = _DIR / "icefall"
_ZIPFORMER = _ICEFALL / "egs" / "librispeech" / "ASR" / "zipformer"
_WEIGHTS = _DIR / "weights"

# Add icefall source directories to Python path so we can import
# model definitions, training helpers, and decoding utilities.
sys.path.insert(0, str(_ICEFALL))
sys.path.insert(0, str(_ZIPFORMER))

# =====================================================================
# Section 3: Icefall Imports (available only after path setup above)
# =====================================================================
from icefall.checkpoint import load_checkpoint  # loads .pt checkpoint
from icefall.utils import AttributeDict  # dict with dot access
from decode_stream import DecodeStream as _BaseDecodeStream  # feature-level stream
from streaming_decode import decode_one_chunk, get_init_states
from train import add_model_arguments, get_model, get_params

# =====================================================================
# Section 4: Load User Config
# =====================================================================
# All tunable hyperparameters live in config.yaml.
# This keeps model.py clean — just edit config.yaml to experiment.
config = OmegaConf.load(_DIR / "config.yaml")


# =====================================================================
# Section 5: DecodeStream — Audio Waveform to Feature Bridge
# =====================================================================
class DecodeStream(_BaseDecodeStream):
    """Extends icefall's DecodeStream to accept raw audio waveforms.

    The base class only works with pre-computed features. This subclass
    adds accept_waveform(), input_finished(), and is_ready().

    Two feature modes (config.yaml -> features.mode):
      - "full":        recompute all features each time  (O(n²), simple)
      - "incremental": only compute new features         (O(n), lower latency)
    """

    _FRAME_SHIFT_MS = 10.0  # Kaldi default frame shift
    _FRAME_LENGTH_MS = 25.0  # Kaldi default frame length

    def __init__(
        self,
        *args,
        sample_rate: int = config.audio.sample_rate,
        incremental: bool = False,
        **kwargs,
    ):
        device = kwargs.get("device", torch.device("cpu"))
        super().__init__(*args, **kwargs)
        self._sample_rate = sample_rate
        self._audio_samples: List[torch.Tensor] = []  # accumulated raw audio
        self._is_input_finished = False
        self._incremental = incremental

        # Configure the Fbank (filter-bank) feature extractor.
        # Fbank converts raw audio waveforms into 80-dim mel-spectrogram
        # features — the standard input format for speech models.
        opts = FbankOptions()
        opts.device = device
        opts.frame_opts.dither = 0  # disable dither for deterministic output
        opts.mel_opts.num_bins = 80  # 80-dimensional mel features
        self._fbank = Fbank(opts)

        # Incremental mode state
        if incremental:
            self._num_stable_frames = 0
            self._total_audio_samples = 0
            self._frame_shift = int(sample_rate * self._FRAME_SHIFT_MS / 1000)
            self._frame_length = int(sample_rate * self._FRAME_LENGTH_MS / 1000)

    def accept_waveform(self, sample_rate: int, waveform):
        """Accept a chunk of raw audio waveform and compute features."""
        if isinstance(waveform, np.ndarray):
            waveform = torch.from_numpy(waveform)
        self._audio_samples.append(waveform)
        if self._incremental:
            self._total_audio_samples += waveform.numel()
            self._compute_features_incremental()
        else:
            self._recompute_features()

    def is_ready(self, chunk_size: int) -> bool:
        """Check if we have enough feature frames to decode one chunk."""
        return (
            self.num_frames - self.num_processed_frames
        ) >= chunk_size * 2 + self.pad_length

    def input_finished(self):
        """Mark audio input as complete and pad features for the encoder tail."""
        self._is_input_finished = True
        if self._incremental:
            self._compute_features_incremental()
        else:
            self._recompute_features()

    # ----- Full recomputation mode (original baseline) -----------------

    def _recompute_features(self):
        """Concatenate all received audio, extract Fbank features, store them.

        Called after every new audio chunk. Re-extracts features from ALL
        accumulated audio (simple but correct for a baseline).
        """
        if not self._audio_samples:
            return
        audio = torch.cat(self._audio_samples)
        feats = self._fbank(audio)
        # When audio is finished, pad with silence (LOG_EPS) so the encoder
        # can process the remaining frames that need right-context.
        if self._is_input_finished:
            feats = torch.nn.functional.pad(
                feats,
                (0, 0, 0, self.pad_length + 30),
                mode="constant",
                value=self.LOG_EPS,
            )
        self.features = feats
        self.num_frames = feats.size(0)

    # ----- Incremental computation mode (sherpa-onnx style) ------------

    def _compute_features_incremental(self):
        """Compute Fbank features only for new audio, append to cache.

        Uses a 1-frame overlap to preserve Kaldi pre-emphasis continuity:
        the overlap frame is recomputed but discarded, so all kept frames
        are bit-exact with the full-recomputation result.
        """
        if not self._audio_samples:
            return

        fs = self._frame_shift
        fl = self._frame_length

        if self._num_stable_frames == 0:
            # First computation
            if self._total_audio_samples >= fl:
                audio = torch.cat(self._audio_samples)
                self._audio_samples = [audio]
                self.features = self._fbank(audio)
                self._num_stable_frames = self.features.size(0)
        else:
            # Incremental: overlap 1 frame, drop it, keep the rest
            overlap_sample = (self._num_stable_frames - 1) * fs
            available = self._total_audio_samples - overlap_sample

            if available >= fl + fs:  # enough for overlap + ≥1 new frame
                audio = torch.cat(self._audio_samples)
                self._audio_samples = [audio]
                new_feats = self._fbank(audio[overlap_sample:])
                new_feats = new_feats[1:]  # drop overlap frame
                if new_feats.size(0) > 0:
                    self.features = torch.cat([self.features, new_feats], dim=0)
                    self._num_stable_frames = self.features.size(0)

        # Pad when audio input is complete
        if self._is_input_finished:
            if self._num_stable_frames > 0:
                self.features = torch.nn.functional.pad(
                    self.features,
                    (0, 0, 0, self.pad_length + 30),
                    mode="constant",
                    value=self.LOG_EPS,
                )
            else:
                device = (
                    self._audio_samples[0].device
                    if self._audio_samples
                    else torch.device("cpu")
                )
                self.features = torch.full(
                    (self.pad_length + 30, 80),
                    self.LOG_EPS,
                    device=device,
                )

        if self._is_input_finished or self._num_stable_frames > 0:
            self.num_frames = self.features.size(0)


# =====================================================================
# Section 6: Model — Public Interface for the Ingestion Program
# =====================================================================
class Model:
    """Streaming ASR model with 5 required methods.

    Lifecycle:
      model.set_partial_callback(fn)          # register callback (once)
      model.reset()                           # prepare for new file
      for chunk in audio_chunks:
          partial = model.accept_chunk(chunk)  # get partial text
      final = model.input_finished()          # get final text
    """

    def __init__(self):
        print("Loading streaming zipformer model …")
        self._device = torch.device("cpu")
        self._partial_callback = None

        # Step 1: Build the unified parameter dictionary.
        #   Merges icefall defaults with our config.yaml settings.
        self._params = self._build_params()

        # Step 2: Load the BPE tokenizer.
        #   BPE (Byte-Pair Encoding) maps between text and token IDs.
        #   The model predicts token IDs; the tokenizer decodes them to text.
        self._sp = spm.SentencePieceProcessor()
        self._sp.load(self._params.bpe_model)
        self._params.blank_id = self._sp.piece_to_id("<blk>")  # blank (transducer)
        self._params.unk_id = self._sp.piece_to_id("<unk>")  # unknown token
        self._params.vocab_size = self._sp.get_piece_size()  # vocabulary size

        # Step 3: Load the acoustic model (Zipformer encoder + Transducer decoder).
        self._model = get_model(self._params)
        load_checkpoint(
            f"{self._params.exp_dir}/epoch-{self._params.epoch}.pt",
            self._model,
        )
        self._model.to(self._device).eval()  # move to device & set inference mode
        self._model.device = self._device

        self._stream = None  # created fresh in reset() for each audio file
        print(f"Model loaded on {self._device}")

    # -----------------------------------------------------------------
    # Streaming Interface (called by the ingestion program)
    # -----------------------------------------------------------------

    def set_partial_callback(self, callback) -> None:
        """Register a callback for partial results: callback(text: str)."""
        self._partial_callback = callback

    def reset(self) -> None:
        """Reset state for a new audio file. Call once before each file."""
        incremental = (
            OmegaConf.select(config, "features.mode", default="full") == "incremental"
        )
        self._stream = DecodeStream(
            params=self._params,
            cut_id="streaming",
            initial_states=get_init_states(self._model, 1, self._device),
            decoding_graph=None,
            device=self._device,
            incremental=incremental,
        )

    def accept_chunk(self, audio_chunk: np.ndarray) -> str:
        """Feed one audio chunk (float32, 16 kHz) and return partial transcription."""
        self._stream.accept_waveform(
            config.audio.sample_rate, torch.from_numpy(audio_chunk)
        )
        self._decode_available()
        return self._sp.decode(self._stream.decoding_result())

    def input_finished(self) -> str:
        """Signal end of audio and return the final transcription."""
        # Append 0.3 s of silence so the model can flush its internal buffer.
        tail = np.zeros(int(config.audio.sample_rate * 0.3), dtype=np.float32)
        self._stream.accept_waveform(config.audio.sample_rate, torch.from_numpy(tail))
        self._stream.input_finished()
        self._decode_available()
        return self._sp.decode(self._stream.decoding_result())

    # -----------------------------------------------------------------
    # Private Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _build_params() -> AttributeDict:
        """Build the complete parameter dictionary for the model.

        Three sources are merged (later overrides earlier):
          1. get_params()            — icefall's basic defaults
             (feature_dim, search settings, etc.)
          2. add_model_arguments()   — Zipformer architecture defaults
             (attention heads, feedforward dims, num layers, etc.)
             We parse an empty arg list [] to collect all defaults.
          3. config.yaml overrides   — our custom settings
             (chunk_size, beam width, etc. — HIGHEST priority)
        """
        # --- Source 1: icefall basic defaults ---
        params = get_params()

        # --- Source 2: Zipformer architecture defaults via argparse ---
        parser = argparse.ArgumentParser()
        add_model_arguments(parser)
        parser.set_defaults(
            chunk_size=str(config.encoder.chunk_size),
            left_context_frames=str(config.encoder.left_context_frames),
            causal=True,  # must be True for streaming
        )
        params.update(vars(parser.parse_args([])))

        # --- Source 3: config.yaml values (highest priority) ---
        params.sample_rate = config.audio.sample_rate
        params.epoch = config.weights.epoch
        params.chunk_size = str(config.encoder.chunk_size)
        params.left_context_frames = str(config.encoder.left_context_frames)
        params.context_size = config.decoder.context_size
        params.decoding_method = config.decoding.method
        params.num_active_paths = config.decoding.num_active_paths

        # --- File paths (derived from _WEIGHTS) ---
        params.exp_dir = str(_WEIGHTS / "exp")
        params.bpe_model = str(_WEIGHTS / "data" / "lang_bpe_500" / "bpe.model")

        return params

    def _decode_available(self):
        """Decode as many chunks as the stream currently has ready."""
        while (
            self._stream.is_ready(config.encoder.chunk_size) and not self._stream.done
        ):
            if decode_one_chunk(self._params, self._model, [self._stream]):
                break
            # Notify ingestion of partial result via callback
            text = self._sp.decode(self._stream.decoding_result())
            self._partial_callback(text)
