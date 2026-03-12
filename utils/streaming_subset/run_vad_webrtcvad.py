#!/usr/bin/env python3
"""
Run WebRTC VAD on filtered audio (multiprocessing).
Trims leading/trailing silence and exports VAD-aware CSV columns.

Usage:
    python run_vad_webrtcvad.py \
        --input-csv /path/to/input.csv \
        --audio-root /path/to/data_root \
        --output-csv /path/to/output_vad.csv \
        --aggressiveness 2 \
        --num-workers 8
"""

import argparse
import csv
import wave
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from pathlib import Path

import webrtcvad
from tqdm import tqdm


def read_wave(path):
    """Read a WAV file and return (PCM bytes, sample_rate, sample_width)."""
    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        pcm_data = wf.readframes(n_frames)

        assert n_channels == 1, f"Only mono WAV is supported, got {n_channels} channels"
        assert (
            sample_width == 2
        ), f"Only 16-bit WAV is supported, got {sample_width * 8} bit"
        assert sample_rate in (
            8000,
            16000,
            32000,
            48000,
        ), f"webrtcvad supports only 8/16/32/48 kHz, got {sample_rate} Hz"

    return pcm_data, sample_rate, sample_width


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Split audio bytes into fixed-size frames."""
    n = int(
        sample_rate * (frame_duration_ms / 1000.0) * 2
    )  # 2 bytes per sample (16-bit)
    offset = 0
    while offset + n <= len(audio):
        yield audio[offset : offset + n], offset
        offset += n


def vad_segments(
    audio_path,
    aggressiveness=2,
    frame_duration_ms=30,
    min_speech_ms=250,
    merge_gap_ms=300,
):
    """Run VAD and return speech boundaries/statistics."""
    pcm_data, sample_rate, _ = read_wave(audio_path)
    vad = webrtcvad.Vad(aggressiveness)

    frames = list(frame_generator(frame_duration_ms, pcm_data, sample_rate))
    total_duration_s = len(pcm_data) / (sample_rate * 2)  # 2 bytes per sample

    if not frames:
        return {
            "speech_ratio": 0.0,
            "speech_start": 0.0,
            "speech_end": round(total_duration_s, 3),
            "speech_duration_s": 0.0,
            "total_duration_s": round(total_duration_s, 3),
            "n_segments": 0,
        }

    # Per-frame VAD decision.
    is_speech = []
    for frame_bytes, offset in frames:
        try:
            is_speech.append(vad.is_speech(frame_bytes, sample_rate))
        except Exception:
            is_speech.append(False)

    n_total = len(is_speech)
    n_speech = sum(is_speech)
    frame_dur_s = frame_duration_ms / 1000.0

    # Step 1: Extract contiguous speech segments (start_idx, end_idx).
    raw_segments = []
    in_speech = False
    seg_start = 0
    for i, s in enumerate(is_speech):
        if s and not in_speech:
            seg_start = i
            in_speech = True
        elif not s and in_speech:
            raw_segments.append((seg_start, i))
            in_speech = False
    if in_speech:
        raw_segments.append((seg_start, len(is_speech)))

    if not raw_segments:
        return {
            "speech_ratio": 0.0,
            "speech_start": 0.0,
            "speech_end": round(total_duration_s, 3),
            "speech_duration_s": 0.0,
            "total_duration_s": round(total_duration_s, 3),
            "n_segments": 0,
        }

    # Step 2: Merge neighboring segments with short gaps.
    merge_gap_frames = int(merge_gap_ms / frame_duration_ms)
    merged = [raw_segments[0]]
    for seg_start, seg_end in raw_segments[1:]:
        prev_start, prev_end = merged[-1]
        if seg_start - prev_end <= merge_gap_frames:
            merged[-1] = (prev_start, seg_end)
        else:
            merged.append((seg_start, seg_end))

    # Step 3: Drop very short segments (< min_speech_ms).
    min_frames = int(min_speech_ms / frame_duration_ms)
    segments = [(s, e) for s, e in merged if (e - s) >= min_frames]

    if not segments:
        # Fallback to merged segments if all were removed.
        segments = merged

    # Aggregate stats.
    speech_start_s = segments[0][0] * frame_dur_s
    speech_end_s = segments[-1][1] * frame_dur_s

    speech_duration_s = sum((e - s) * frame_dur_s for s, e in segments)

    return {
        "speech_ratio": n_speech / n_total if n_total > 0 else 0.0,
        "speech_start": round(speech_start_s, 3),
        "speech_end": round(min(speech_end_s, total_duration_s), 3),
        "speech_duration_s": round(speech_duration_s, 3),
        "total_duration_s": round(total_duration_s, 3),
        "n_segments": len(segments),
    }


def process_one(args_tuple):
    """Process one row for multiprocessing."""
    row, audio_root, aggressiveness, frame_duration = args_tuple
    audio_path = Path(audio_root) / row["audio_filepath"]

    if not audio_path.exists():
        return None, row

    result = vad_segments(str(audio_path), aggressiveness, frame_duration)

    out_row = dict(row)
    out_row["speech_start"] = result["speech_start"]
    out_row["speech_end"] = result["speech_end"]
    out_row["speech_duration"] = result["speech_duration_s"]
    out_row["speech_ratio"] = round(result["speech_ratio"], 4)

    return result, out_row


def main():
    parser = argparse.ArgumentParser(description="WebRTC VAD (multiprocessing)")
    parser.add_argument("--input-csv", required=True, help="Input manifest CSV")
    parser.add_argument(
        "--audio-root", required=True, help="Audio root prefix for audio_filepath"
    )
    parser.add_argument("--output-csv", required=True, help="Output CSV path")
    parser.add_argument(
        "--aggressiveness",
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help="VAD aggressiveness (0=least, 3=most, default=2)",
    )
    parser.add_argument(
        "--frame-duration",
        type=int,
        default=30,
        choices=[10, 20, 30],
        help="Frame duration in ms (default=30)",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=16,
        help=f"Worker processes (default=16, available CPUs: {cpu_count()})",
    )
    args = parser.parse_args()

    audio_root = Path(args.audio_root)

    # Read input CSV.
    with open(args.input_csv, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Input: {args.input_csv}")
    print(f"Rows: {len(rows)}")
    print(
        f"VAD config: aggressiveness={args.aggressiveness}, frame_duration={args.frame_duration}ms"
    )
    print(f"Workers: {args.num_workers}")
    print()

    # Build tasks.
    task_args = [
        (row, str(audio_root), args.aggressiveness, args.frame_duration) for row in rows
    ]

    # Multiprocessing with progress bar.
    stats = defaultdict(list)
    output_rows = []
    n_missing = 0

    with Pool(processes=args.num_workers) as pool:
        for result, out_row in tqdm(
            pool.imap(process_one, task_args, chunksize=64),
            total=len(rows),
            desc="VAD processing",
            unit="file",
        ):
            if result is None:
                n_missing += 1
                continue

            output_rows.append(out_row)
            stats["speech_ratio"].append(result["speech_ratio"])
            stats["speech_duration"].append(result["speech_duration_s"])
            stats["speech_start"].append(result["speech_start"])
            stats["speech_end"].append(result["speech_end"])

    # Write output CSV.
    if output_rows:
        fieldnames = list(output_rows[0].keys())
        with open(args.output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

    print(f"\nDone. Output: {args.output_csv}")
    print(f"Processed: {len(output_rows)}/{len(rows)}")
    if n_missing > 0:
        print(f"Missing audio files: {n_missing}")

    # Print summary stats.
    if stats["speech_ratio"]:
        ratios = sorted(stats["speech_ratio"])
        durations = sorted(stats["speech_duration"])
        starts = sorted(stats["speech_start"])
        ends = sorted(stats["speech_end"])
        n = len(ratios)

        print(f"\n{'='*50}")
        print(f"  VAD summary")
        print(f"{'='*50}")
        print(f"  Speech ratio:")
        print(f"    Mean: {sum(ratios)/n:.4f}")
        print(
            f"    P10:  {ratios[int(n*0.10)]:.4f}  P50: {ratios[int(n*0.50)]:.4f}  P90: {ratios[int(n*0.90)]:.4f}"
        )
        print(f"  Speech duration (s):")
        print(f"    Mean: {sum(durations)/n:.3f}s")
        print(
            f"    P10:  {durations[int(n*0.10)]:.3f}s  P50: {durations[int(n*0.50)]:.3f}s  P90: {durations[int(n*0.90)]:.3f}s"
        )
        print(f"  Speech start (s):")
        print(f"    Mean: {sum(starts)/n:.3f}s")
        print(
            f"    P10:  {starts[int(n*0.10)]:.3f}s  P50: {starts[int(n*0.50)]:.3f}s  P90: {starts[int(n*0.90)]:.3f}s"
        )
        print(f"  Speech end (s):")
        print(f"    Mean: {sum(ends)/n:.3f}s")
        print(
            f"    P10:  {ends[int(n*0.10)]:.3f}s  P50: {ends[int(n*0.50)]:.3f}s  P90: {ends[int(n*0.90)]:.3f}s"
        )

        print(f"\n  Speech ratio distribution:")
        bins = [(0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]
        for lo, hi in bins:
            count = sum(1 for r in ratios if lo <= r < hi)
            pct = count / n * 100
            bar = "#" * int(pct + 0.5)
            label = f"{lo:.0%}-{hi:.0%}" if hi <= 1.0 else f"{lo:.0%}-100%"
            print(f"    {label:>10s}: {count:6d} ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()
