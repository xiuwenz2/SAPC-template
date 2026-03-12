#!/usr/bin/env python3
"""Simplified local decoder for Track 2 streaming submissions."""

import argparse
import csv
import json
import os
import queue
import sys
import threading
import time
import wave
from pathlib import Path

SAMPLE_RATE = 16000
CHUNK_SIZE = 1600


def setup_environment(submission_dir: Path):
    setup_script = submission_dir / "setup.sh"
    if setup_script.exists():
        import subprocess

        print("Running setup.sh...")
        subprocess.check_call(["bash", str(setup_script)])


def load_manifest(manifest_path: Path, data_root: Path):
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    entries = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio_path = data_root / row["audio_filepath"]
            entries.append((row["id"], str(audio_path)))

    print(f"Found {len(entries)} audio files in manifest {manifest_path}")
    return entries


def read_wave(wave_path: str):
    import numpy as np

    with wave.open(wave_path, "rb") as f:
        if f.getframerate() != SAMPLE_RATE:
            raise ValueError(f"Expected {SAMPLE_RATE}Hz, got {f.getframerate()}Hz")
        if f.getnchannels() != 1:
            raise ValueError(f"Expected mono, got {f.getnchannels()} channels")
        if f.getsampwidth() != 2:
            raise ValueError(f"Expected 16-bit, got {f.getsampwidth() * 8}-bit")
        samples = f.readframes(f.getnframes())
    return np.frombuffer(samples, dtype=np.int16).astype(np.float32) / 32768.0


def run_batch_decode(model, entries, chunk_size: int):
    ids = []
    predictions = []
    for i, (uid, audio_path) in enumerate(entries, start=1):
        if i % 100 == 0:
            print(f"[Batch] Progress: {i}/{len(entries)}")
        samples = read_wave(audio_path)
        model.reset()
        model.set_partial_callback(lambda _text: None)
        for start in range(0, len(samples), chunk_size):
            model.accept_chunk(samples[start : start + chunk_size])
        ids.append(uid)
        predictions.append(model.input_finished())
    return ids, predictions


def run_streaming_decode(model, entries, chunk_size: int, streaming_interval: float):
    all_partial_results = {}
    for i, (uid, audio_path) in enumerate(entries, start=1):
        if i % 100 == 0:
            print(f"[Streaming] Progress: {i}/{len(entries)}")

        samples = read_wave(audio_path)
        events = []
        audio_duration = len(samples) / SAMPLE_RATE
        timing = {}

        def on_partial(text: str):
            ts = time.time()
            events.append({"event": "partial_callback", "time": ts, "text": text})
            if "first_partial_time" not in timing:
                timing["first_partial_time"] = ts

        model.set_partial_callback(on_partial)
        audio_queue = queue.Queue()
        sender_done = threading.Event()
        final_text_holder = [""]
        finalized = [False]

        def audio_sender():
            first_send_ts = None
            for start in range(0, len(samples), chunk_size):
                now = time.time()
                if first_send_ts is None:
                    first_send_ts = now
                audio_queue.put(samples[start : start + chunk_size])
                if streaming_interval > 0:
                    time.sleep(streaming_interval)
            audio_queue.put(None)
            if first_send_ts is not None:
                timing["audio_send_start_time"] = first_send_ts
                timing["audio_end_oracle_time"] = first_send_ts + audio_duration
            sender_done.set()

        def decoder():
            model.reset()
            while True:
                try:
                    chunk = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if sender_done.is_set():
                        if not finalized[0]:
                            final_text_holder[0] = model.input_finished() or ""
                            finalized[0] = True
                        break
                    continue

                if chunk is None:
                    if not finalized[0]:
                        final_text_holder[0] = model.input_finished() or ""
                        finalized[0] = True
                    break
                model.accept_chunk(chunk)

        t_sender = threading.Thread(target=audio_sender, name="AudioSender")
        t_decoder = threading.Thread(target=decoder, name="Decoder")
        t_sender.start()
        t_decoder.start()
        t_sender.join()
        t_decoder.join()

        final_text = final_text_holder[0]
        final_visible_time = time.time()
        timing["final_visible_time"] = final_visible_time
        events.append(
            {"event": "final_visible", "time": final_visible_time, "text": final_text}
        )

        all_partial_results[uid] = {"events": events, "timing": timing}

    return all_partial_results


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-dir", required=True, type=Path)
    parser.add_argument("--manifest-csv", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--out-csv", type=Path, default=Path("./predict.csv"))
    parser.add_argument(
        "--streaming-manifest-csv",
        type=Path,
        default=None,
        help="If not set, use --manifest-csv for streaming pass.",
    )
    parser.add_argument(
        "--out-partial-json", type=Path, default=Path("./partial_results.json")
    )
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--streaming-interval", type=float, default=0.1)
    return parser.parse_args()


def main():
    args = parse_args()
    sys.path.append(str(args.submission_dir))

    print("Ingestion program - Streaming ASR (Local Dev)")
    setup_environment(args.submission_dir)

    from model import Model

    model = Model()

    batch_entries = load_manifest(args.manifest_csv, args.data_root)
    ids, predictions = run_batch_decode(model, batch_entries, args.chunk_size)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "raw_hypos"])
        for uid, pred in zip(ids, predictions):
            writer.writerow([uid, pred])
    print(f"Predictions saved to {args.out_csv}")

    streaming_manifest = args.streaming_manifest_csv or args.manifest_csv
    streaming_entries = load_manifest(streaming_manifest, args.data_root)
    partial_results = run_streaming_decode(
        model, streaming_entries, args.chunk_size, args.streaming_interval
    )
    args.out_partial_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_partial_json, "w", encoding="utf-8") as f:
        json.dump(partial_results, f, ensure_ascii=False, indent=2)
    print(f"Partial results saved to {args.out_partial_json}")
    print("Completed")


if __name__ == "__main__":
    main()
