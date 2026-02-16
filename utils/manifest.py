#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path
from glob import glob
import pandas as pd
import re
from tqdm import tqdm
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor, as_completed


def extract_records_from_json(path: Path):
    """
    Extract records from a single JSON file.

    Expected structure:
    {
      "Etiology": "Cerebral Palsy",   # optional
      "Files": [
        {
          "Filename": "...wav",
          "Prompt": {"Transcript": "..."}
        }
      ]
    }

    Returns: list of dicts with keys: wav, raw_trans, etiology
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] failed to read: {path} ({e})")
        return []

    etiology = str(data.get("Etiology", "") or "").strip()
    files = data.get("Files", [])
    if not isinstance(files, list):
        return []

    records = []
    seen = set()
    for item in files:
        if not isinstance(item, dict):
            continue

        filename = item.get("Filename")
        transcript = (item.get("Prompt", {}) or {}).get("Transcript")
        if not filename or transcript is None:
            continue

        wav = Path(str(filename).strip()).name
        if wav in seen:
            continue
        seen.add(wav)

        records.append(
            {
                "wav": wav,
                "raw_trans": str(transcript).strip(),
                "etiology": etiology,
            }
        )
    return records


def collect_records(json_dir: Path):
    """
    Collect records from JSON files in speaker subdirectories.
    Structure: json_dir/speaker_id/speaker_id.json
    On conflicts, keep the first seen and warn.
    """
    if not json_dir.is_dir():
        print(f"[WARN] JSON directory does not exist: {json_dir}")
        return []

    # Find all speaker subdirectories
    speaker_dirs = [d for d in json_dir.iterdir() if d.is_dir()]
    if not speaker_dirs:
        print(f"[INFO] no speaker subdirectories found under: {json_dir}")
        return []

    print(f"[INFO] Found {len(speaker_dirs)} speaker directories")

    merged = {}  # wav -> record
    json_count = 0

    # Process each speaker directory
    for speaker_dir in tqdm(
        sorted(speaker_dirs), desc="Processing speaker directories"
    ):
        # Look for JSON files in this speaker directory
        json_files = list(speaker_dir.glob("*.json"))
        if not json_files:
            continue

        for jp in sorted(json_files):
            json_count += 1
            for rec in extract_records_from_json(jp):
                wav = rec["wav"]
                if wav not in merged:
                    merged[wav] = rec
                else:
                    prev = merged[wav]
                    if prev["raw_trans"] != rec["raw_trans"] or prev.get(
                        "etiology", ""
                    ) != rec.get("etiology", ""):
                        print(
                            f"[WARN] cross-file conflict for {wav}; keeping first seen, ignoring {jp}"
                        )

    print(
        f"[INFO] Processed {json_count} JSON files from {len(speaker_dirs)} speaker directories"
    )
    return list(merged.values())


def clean_transcript(text: str) -> str:
    """Clean transcript text."""
    if not text:
        return ""
    text = re.sub(r"^#dis\s*\n", "", text, count=1)
    text = re.sub(r"\n", "", text)
    return text


def read_txt_file(txt_path: Path):
    """
    Read txt file with format: <wav_path>\t<etiology>
    Returns: list of tuples (wav_filename, etiology) in file order
    """
    records = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            wav = Path(parts[0].strip()).name
            etiology = parts[1].strip()
            records.append((wav, etiology))
    return records


def get_duration_safe(path: Path):
    """Get audio duration, return None if file doesn't exist or cannot be read."""
    try:
        return sf.info(path).duration
    except Exception:
        return None


def build_manifest_from_txt(
    txt_path: Path,
    transcript_lookup: dict,
    data_root: Path,
    split: str,
    workers: int = 8,
) -> pd.DataFrame:
    """
    Build manifest DataFrame from txt file, preserving file order.
    transcript_lookup: dict mapping wav -> {"raw_trans": ..., "etiology": ...}
    """
    txt_records = read_txt_file(txt_path)
    print(f"[INFO] Read {len(txt_records)} entries from txt file.")

    # Setup log file for missing files
    log_dir = data_root / "processed" / split
    log_file = log_dir / "_errors2.log"
    missing_files = []  # Missing audio files
    missing_transcript_files = []  # Missing transcript files

    # First pass: prepare all paths and filter valid entries
    valid_entries = []
    missing_count = 0
    for wav, etiology_from_txt in txt_records:
        # Extract speaker_id from wav filename (format: speaker_id_number_number.wav)
        speaker_id = wav.split("_")[0] if "_" in wav else None
        if not speaker_id:
            print(f"[WARN] Cannot extract speaker_id from {wav}, skipping")
            missing_count += 1
            continue

        # Build path: processed/{split}/{speaker_id}/{wav}
        path = data_root / "processed" / split / speaker_id / wav

        transcript_info = transcript_lookup.get(wav)
        if transcript_info is None:
            missing_count += 1
            missing_transcript_files.append(str(path))
            if missing_count <= 10:
                print(f"[WARN] No transcript found for {wav}")
            continue

        raw_trans = clean_transcript(transcript_info.get("raw_trans", ""))
        etiology = etiology_from_txt or transcript_info.get("etiology", "")

        valid_entries.append(
            {
                "wav": wav,
                "path": path,
                "speaker_id": speaker_id,
                "etiology": etiology,
                "raw_trans": raw_trans,
            }
        )

    # Second pass: parallel get durations
    print(
        f"[INFO] Getting durations for {len(valid_entries)} files using {workers} workers..."
    )
    duration_map = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_path = {
            executor.submit(get_duration_safe, entry["path"]): entry
            for entry in valid_entries
        }
        for future in tqdm(
            as_completed(future_to_path),
            total=len(valid_entries),
            desc="Getting durations",
        ):
            entry = future_to_path[future]
            duration = future.result()
            if duration is None:
                missing_files.append(str(entry["path"]))
            else:
                duration_map[entry["path"]] = duration

    # Third pass: build rows
    rows = []
    for entry in valid_entries:
        path = entry["path"]
        if path not in duration_map:
            continue  # Skip missing files

        # id is filename without .wav extension
        file_id = Path(entry["wav"]).stem

        # audio_filepath: relative to data_root
        audio_filepath = str(path.relative_to(data_root))

        row = {
            "id": file_id,
            "speaker": entry["speaker_id"],
            "etiology": entry["etiology"],
            "audio_filepath": audio_filepath,
            "duration": duration_map[path],
            "text": entry["raw_trans"],
        }
        rows.append(row)

    # Write missing files to log
    log_dir.mkdir(parents=True, exist_ok=True)
    if missing_files or missing_transcript_files:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Missing files for split: {split}\n")
            f.write(
                f"Total missing: {len(missing_files) + len(missing_transcript_files)}\n\n"
            )
            # Write missing transcript files
            for missing_path in missing_transcript_files:
                f.write(f"{missing_path}\n")
            # Write missing audio files
            for missing_path in missing_files:
                f.write(f"{missing_path}\n")

        total_missing = len(missing_files) + len(missing_transcript_files)
        print(
            f"[INFO] Wrote {total_missing} missing files ({len(missing_transcript_files)} missing transcripts, {len(missing_files)} missing audio) to {log_file}"
        )

    if missing_count > 10:
        print(f"[WARN] Total {missing_count} entries missing transcripts.")

    # Define columns in the required order: id, speaker, etiology, audio_filepath, duration, text
    cols = ["id", "speaker", "etiology", "audio_filepath", "duration", "text"]
    df = pd.DataFrame.from_records(rows, columns=cols)

    return df


def parse_args():
    ap = argparse.ArgumentParser(
        description="Generate manifest CSV from JSON files and txt file."
    )
    ap.add_argument("--txt", required=True, help="Input txt file path")
    ap.add_argument(
        "--json-dir",
        required=True,
        help="Directory containing JSON files (processed/<split>)",
    )
    ap.add_argument("--data-root", required=True, help="Data root directory")
    ap.add_argument("--out-csv", required=True, help="Output CSV path")
    ap.add_argument("--split", required=True, help="Split name (e.g., Dev, Train)")
    ap.add_argument(
        "--workers",
        type=int,
        default=32,
        help="Number of parallel workers for getting durations",
    )
    return ap.parse_args()


def main():
    args = parse_args()

    # Build paths
    txt_path = Path(args.txt)
    json_dir = Path(args.json_dir)
    data_root = Path(args.data_root)
    out_csv = Path(args.out_csv)

    print(f"[INFO] Split: {args.split}")
    print(f"[INFO] Txt file: {txt_path}")
    print(f"[INFO] JSON dir: {json_dir}")
    print(f"[INFO] Output CSV: {out_csv}")

    # Validate paths
    if not txt_path.is_file():
        raise FileNotFoundError(f"Txt file not found: {txt_path}")
    if not json_dir.is_dir():
        raise NotADirectoryError(f"JSON dir not found: {json_dir}")

    # Collect transcripts from JSON files
    records = collect_records(json_dir)
    print(f"[OK] Collected {len(records)} items from JSONs.")

    # Build lookup dictionary
    transcript_lookup = {
        rec["wav"]: {
            "raw_trans": rec["raw_trans"],
            "etiology": rec.get("etiology", ""),
        }
        for rec in records
    }

    # Build manifest from txt file (preserves order)
    df = build_manifest_from_txt(
        txt_path=txt_path,
        transcript_lookup=transcript_lookup,
        data_root=data_root,
        split=args.split,
        workers=args.workers,
    )

    # Save output
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"Saved: {out_csv}")


if __name__ == "__main__":
    main()
