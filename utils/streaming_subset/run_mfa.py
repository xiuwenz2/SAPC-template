#!/usr/bin/env python3
"""
Run Montreal Forced Aligner and extract speech boundaries.
Speech start/end are derived from the phones tier (silence phones excluded).

Usage:
    python run_mfa.py \
        --input-csv /path/to/input.csv \
        --audio-root /path/to/data_root \
        --output-csv /path/to/output_mfa.csv \
        --num-workers 64
"""

import argparse
import csv
import os
import shutil
import subprocess
import time
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from pathlib import Path

from tqdm import tqdm

# Silence tokens in MFA phones tier.
SILENCE_TOKENS = {"sil", "sp", "spn", "sil_S", "sil_E", "sil_I", "sil_B", ""}


def parse_textgrid_phones(tg_path):
    """
    Parse a TextGrid and extract non-silence phones:
    [(phone, xmin, xmax), ...]
    """
    with open(tg_path, "r", encoding="utf-8") as f:
        content = f.read()

    phones = []
    in_phones_tier = False
    in_interval = False
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect phones tier.
        if 'name = "phones"' in line:
            in_phones_tier = True
            i += 1
            continue

        # Stop once next tier starts.
        if in_phones_tier and line.startswith("item ["):
            break

        # Detect interval block start.
        if in_phones_tier and line.startswith("intervals ["):
            in_interval = True
            i += 1
            continue

        # Parse xmin/xmax/text inside interval block.
        if in_phones_tier and in_interval and line.startswith("xmin"):
            xmin = float(line.split("=")[1].strip())
            i += 1
            xmax = float(lines[i].strip().split("=")[1].strip())
            i += 1
            text_line = lines[i].strip()
            text = text_line.split("=", 1)[1].strip().strip('"')
            in_interval = False
            if text not in SILENCE_TOKENS:
                phones.append((text, xmin, xmax))

        i += 1

    return phones


def _prepare_one(args_tuple):
    """Prepare one utterance for MFA (multiprocessing worker)."""
    row, audio_root, corpus_dir, text_column = args_tuple
    audio_path = Path(audio_root) / row["audio_filepath"]
    if not audio_path.exists():
        return None

    speaker = row["speaker"]
    utt_id = row["id"]
    text = row.get(text_column, row.get("text", ""))
    if not text.strip():
        return None

    spk_dir = Path(corpus_dir) / speaker
    spk_dir.mkdir(parents=True, exist_ok=True)

    wav_link = spk_dir / f"{utt_id}.wav"
    if not wav_link.exists():
        os.symlink(str(audio_path.resolve()), str(wav_link))

    lab_file = spk_dir / f"{utt_id}.lab"
    with open(lab_file, "w") as f:
        f.write(text.strip())

    return row


def prepare_corpus(
    rows,
    audio_root,
    corpus_dir,
    text_column="norm_text_without_disfluency",
    num_workers=64,
):
    """Prepare MFA corpus directory (multiprocessing)."""
    task_args = [(row, audio_root, corpus_dir, text_column) for row in rows]

    prepared = []
    with Pool(processes=num_workers) as pool:
        for result in tqdm(
            pool.imap(_prepare_one, task_args, chunksize=128),
            total=len(rows),
            desc="Preparing corpus",
            unit="file",
        ):
            if result is not None:
                prepared.append(result)

    return prepared


def run_mfa_align(corpus_dir, output_dir, num_workers=64):
    """Run `mfa align` and stream logs."""
    cmd = [
        "mfa",
        "align",
        str(corpus_dir),
        "english_mfa",  # dictionary
        "english_mfa",  # acoustic model
        str(output_dir),
        "--num_jobs",
        str(num_workers),
        "--clean",
        "--overwrite",
        "--single_speaker",
    ]

    print(f"  MFA command: {' '.join(cmd)}")
    print(f"  Start time: {time.strftime('%H:%M:%S')}")
    t0 = time.time()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in process.stdout:
        print(f"  [MFA] {line}", end="")
    process.wait()

    elapsed = time.time() - t0
    mins, secs = divmod(int(elapsed), 60)
    print(f"\n  MFA elapsed: {mins}m{secs}s")

    if process.returncode != 0:
        print(f"  [WARN] MFA return code: {process.returncode}")

    return process.returncode


def _collect_one(args_tuple):
    """Parse one TextGrid file (multiprocessing worker)."""
    row, textgrid_dir = args_tuple
    utt_id = row["id"]
    speaker = row["speaker"]

    tg_path = Path(textgrid_dir) / speaker / f"{utt_id}.TextGrid"
    out_row = dict(row)

    if tg_path.exists():
        phones = parse_textgrid_phones(str(tg_path))
        if phones:
            speech_start = phones[0][1]  # xmin of first non-silence phone
            speech_end = phones[-1][2]  # xmax of last non-silence phone
            speech_duration = speech_end - speech_start
            status = "found"
        else:
            speech_start = 0.0
            speech_end = float(row["duration"])
            speech_duration = speech_end
            status = "empty"
    else:
        speech_start = 0.0
        speech_end = float(row["duration"])
        speech_duration = speech_end
        status = "missing"

    out_row["speech_start"] = round(speech_start, 3)
    out_row["speech_end"] = round(speech_end, 3)
    out_row["speech_duration"] = round(speech_duration, 3)
    return out_row, status


def collect_results(rows, textgrid_dir, num_workers=64):
    """Collect alignment results from TextGrids (multiprocessing)."""
    task_args = [(row, textgrid_dir) for row in rows]

    results = []
    n_found = 0
    n_missing = 0

    with Pool(processes=num_workers) as pool:
        for out_row, status in tqdm(
            pool.imap(_collect_one, task_args, chunksize=128),
            total=len(rows),
            desc="Parsing TextGrids",
            unit="file",
        ):
            results.append(out_row)
            if status == "found":
                n_found += 1
            elif status == "missing":
                n_missing += 1

    return results, n_found, n_missing


def main():
    parser = argparse.ArgumentParser(description="Montreal Forced Aligner processing")
    parser.add_argument("--input-csv", required=True, help="Input manifest CSV")
    parser.add_argument("--audio-root", required=True, help="Audio root directory")
    parser.add_argument("--output-csv", required=True, help="Output CSV path")
    parser.add_argument(
        "--num-workers",
        type=int,
        default=64,
        help=f"Worker processes (default=64, available CPUs: {cpu_count()})",
    )
    parser.add_argument(
        "--text-column",
        default="norm_text_without_disfluency",
        help="Transcript column name (default: norm_text_without_disfluency)",
    )
    parser.add_argument(
        "--textgrid-dir",
        default=None,
        help="Existing TextGrid dir (skip MFA align and only parse)",
    )
    args = parser.parse_args()

    # Read input CSV.
    with open(args.input_csv, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Input: {args.input_csv}")
    print(f"Rows: {len(rows)}")
    print(f"Transcript column: {args.text_column}")
    print(f"Workers: {args.num_workers}")
    print()

    # Alignment artifacts are kept under a fixed directory.
    aligned_base = Path(args.output_csv).parent / "mfa_aligned"
    set_name = Path(args.input_csv).stem  # e.g. "subset"
    corpus_dir = aligned_base / f"{set_name}_corpus"
    textgrid_dir = args.textgrid_dir or str(aligned_base / f"{set_name}_textgrid")
    textgrid_dir = str(textgrid_dir)

    if args.textgrid_dir:
        print(f"Using existing TextGrid dir: {textgrid_dir}\n")
    else:
        corpus_dir.mkdir(parents=True, exist_ok=True)
        Path(textgrid_dir).mkdir(parents=True, exist_ok=True)

        print("Step 1: Prepare MFA corpus...")
        prepared_rows = prepare_corpus(
            rows,
            args.audio_root,
            str(corpus_dir),
            args.text_column,
            num_workers=args.num_workers,
        )
        print(f"  Prepared: {len(prepared_rows)}/{len(rows)}\n")

        print("Step 2: Run MFA forced alignment...")
        ret = run_mfa_align(str(corpus_dir), textgrid_dir, args.num_workers)
        print(f"  MFA return code: {ret}\n")

    print("Step 3: Parse TextGrid phones tier...")
    results, n_found, n_missing = collect_results(
        rows, textgrid_dir, num_workers=args.num_workers
    )

    # Write output CSV.
    if results:
        fieldnames = list(results[0].keys())
        with open(args.output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print(f"\nDone. Output: {args.output_csv}")
    print(f"Aligned rows: {n_found}/{len(rows)}")
    if n_missing > 0:
        print(f"Missing TextGrid files: {n_missing}")

    print(f"TextGrid directory: {textgrid_dir}")

    # Summary.
    if results:
        starts = sorted([r["speech_start"] for r in results])
        ends = sorted([r["speech_end"] for r in results])
        durs = sorted([r["speech_duration"] for r in results])
        n = len(results)

        print(f"\n{'='*50}")
        print(f"  MFA summary (phones tier)")
        print(f"{'='*50}")
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
        print(f"  Speech duration (s):")
        print(f"    Mean: {sum(durs)/n:.3f}s")
        print(
            f"    P10:  {durs[int(n*0.10)]:.3f}s  P50: {durs[int(n*0.50)]:.3f}s  P90: {durs[int(n*0.90)]:.3f}s"
        )


if __name__ == "__main__":
    main()
