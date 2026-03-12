#!/usr/bin/env python3
"""
Sample one utterance per speaker from the input CSV.
Uses a fixed random seed for reproducibility.
"""

import argparse
import csv
import random
from collections import defaultdict


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def main():
    parser = argparse.ArgumentParser(description="Sample one row per speaker")
    parser.add_argument("--input-csv", required=True, help="Input CSV")
    parser.add_argument("--output-csv", required=True, help="Output CSV")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--order-csv",
        default=None,
        help="Optional CSV to control output row order",
    )
    parser.add_argument(
        "--mfa-csv", default=None, help="Optional MFA CSV for extra columns"
    )
    parser.add_argument(
        "--vad-csv", default=None, help="Optional VAD CSV for extra columns"
    )
    args = parser.parse_args()

    with open(args.input_csv, "r", newline="") as f:
        rows = list(csv.DictReader(f))

    by_speaker = defaultdict(list)
    for row in rows:
        spk = row.get("speaker", "")
        if spk:
            by_speaker[spk].append(row)

    rng = random.Random(args.seed)
    sampled = []
    for spk in sorted(by_speaker.keys()):
        sampled.append(rng.choice(by_speaker[spk]))

    # Keep original input order.
    sampled_ids = {r.get("id", "") for r in sampled}
    sampled = [r for r in rows if r.get("id", "") in sampled_ids]

    # If provided, reorder by the reference CSV.
    if args.order_csv:
        with open(args.order_csv, "r", newline="") as f:
            order_rows = list(csv.DictReader(f))
        sampled_map = {r.get("id", ""): r for r in sampled}
        sampled = [
            sampled_map[r.get("id", "")]
            for r in order_rows
            if r.get("id", "") in sampled_map
        ]

    # Optionally enrich with MFA/VAD columns.
    mfa_map = {}
    vad_map = {}
    if args.mfa_csv:
        with open(args.mfa_csv, "r", newline="") as f:
            mfa_map = {r.get("id", ""): r for r in csv.DictReader(f)}
    if args.vad_csv:
        with open(args.vad_csv, "r", newline="") as f:
            vad_map = {r.get("id", ""): r for r in csv.DictReader(f)}

    enriched = []
    for r in sampled:
        row = dict(r)
        uid = row.get("id", "")
        mfa = mfa_map.get(uid, {})
        vad = vad_map.get(uid, {})

        mfa_start = safe_float(mfa.get("speech_start", "nan"), default=float("nan"))
        mfa_end = safe_float(mfa.get("speech_end", "nan"), default=float("nan"))
        vad_start = safe_float(vad.get("speech_start", "nan"), default=float("nan"))
        vad_end = safe_float(vad.get("speech_end", "nan"), default=float("nan"))
        dur = safe_float(row.get("duration", 0.0))

        row["mfa_speech_start"] = f"{mfa_start:.3f}" if mfa else ""
        row["mfa_speech_end"] = f"{mfa_end:.3f}" if mfa else ""
        row["vad_speech_start"] = f"{vad_start:.3f}" if vad else ""
        row["vad_speech_end"] = f"{vad_end:.3f}" if vad else ""
        if vad:
            row["abs_vad_end_minus_duration"] = f"{abs(vad_end - dur):.3f}"
        else:
            row["abs_vad_end_minus_duration"] = ""
        enriched.append(row)

    sampled = enriched

    if sampled:
        with open(args.output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(sampled[0].keys()))
            writer.writeheader()
            writer.writerows(sampled)
    else:
        with open(args.output_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id"])

    in_speakers = len(by_speaker)
    in_duration_h = sum(safe_float(r.get("duration", 0.0)) for r in rows) / 3600.0
    out_duration_h = sum(safe_float(r.get("duration", 0.0)) for r in sampled) / 3600.0

    print(f"Input CSV:     {args.input_csv}")
    print(f"Output CSV:    {args.output_csv}")
    print(f"Seed:          {args.seed}")
    print(f"Input rows:    {len(rows)}")
    print(f"Speakers:      {in_speakers}")
    print(f"Sampled rows:  {len(sampled)} (1 per speaker)")
    print(f"Input hours:   {in_duration_h:.2f}h")
    print(f"Output hours:  {out_duration_h:.2f}h")


if __name__ == "__main__":
    main()
