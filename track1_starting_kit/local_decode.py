#!/usr/bin/env python3
"""Local ingestion-style decoder for Track 1 dev testing."""
import argparse
import csv
import sys
import os
from pathlib import Path


def setup_environment(submission_dir):
    """Run optional setup.sh in submission dir for local dependency setup."""
    setup_script = os.path.join(str(submission_dir), "setup.sh")
    if os.path.exists(setup_script):
        import subprocess

        print("Running setup.sh...")
        subprocess.check_call(["bash", setup_script])


def load_manifest(manifest_path, input_dir):
    """Read manifest CSV and return list of (id, audio_filepath) tuples."""
    if not os.path.exists(str(manifest_path)):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    entries = []
    with open(str(manifest_path), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio_path = os.path.join(str(input_dir), row["audio_filepath"])
            entries.append((row["id"], audio_path))

    print(f"Found {len(entries)} audio files in manifest {manifest_path}")
    return entries


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-dir", required=True, type=Path)
    parser.add_argument("--manifest-csv", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--out-csv", type=Path, default=Path("./predict.csv"))
    return parser.parse_args()


def main():
    args = parse_args()
    sys.path.append(str(args.submission_dir))

    print("Ingestion program - ASR Model (Local Dev)")
    setup_environment(args.submission_dir)

    from model import Model

    model = Model()

    entries = load_manifest(args.manifest_csv, args.data_root)
    ids = []
    predictions = []
    for i, (uid, audio_path) in enumerate(entries):
        if (i + 1) % 100 == 0:
            print(f"Progress: {i + 1}/{len(entries)}")
        ids.append(uid)
        predictions.append(model.predict(audio_path))

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "raw_hypos"])
        for uid, pred in zip(ids, predictions):
            writer.writerow([uid, pred])
    print(f"Predictions saved to {args.out_csv}")

    print("Completed")


if __name__ == "__main__":
    main()
