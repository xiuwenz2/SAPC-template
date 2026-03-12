#!/usr/bin/env python3
"""
Print duration stats for one CSV file and save bin stats to CSV.
"""

import argparse
import csv
import os
from pathlib import Path


def load_durations(path):
    with open(path, "r", newline="") as f:
        rows = list(csv.DictReader(f))
    durations = [float(r["duration"]) for r in rows]
    speakers = {r["speaker"] for r in rows if r.get("speaker")}
    return rows, durations, speakers


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    idx = int(len(sorted_vals) * p)
    if idx >= len(sorted_vals):
        idx = len(sorted_vals) - 1
    return sorted_vals[idx]


def print_stats(name, durations, speakers):
    d = sorted(durations)
    n = len(d)
    total_sec = sum(d)
    total_h = total_sec / 3600.0
    mean = (total_sec / n) if n > 0 else 0.0

    print(f"\n--- {name} ---")
    print(f"files:      {n}")
    print(f"speakers:   {len(speakers)}")
    print(f"total:      {total_sec:.2f}s ({total_h:.2f}h)")
    print(f"mean:       {mean:.3f}s")
    print(f"P10/P25:    {percentile(d,0.10):.3f}s / {percentile(d,0.25):.3f}s")
    print(f"P50/P75:    {percentile(d,0.50):.3f}s / {percentile(d,0.75):.3f}s")
    print(f"P90/P95:    {percentile(d,0.90):.3f}s / {percentile(d,0.95):.3f}s")

    bins = [
        (0, 3, "0-3s"),
        (3, 5, "3-5s"),
        (5, 10, "5-10s"),
        (10, 15, "10-15s"),
        (15, 20, "15-20s"),
        (20, 30, "20-30s"),
        (30, 1e9, "30s+"),
    ]
    print("distribution:")
    for lo, hi, label in bins:
        cnt = sum(1 for x in d if lo <= x < hi)
        pct = (cnt / n * 100.0) if n > 0 else 0.0
        print(f"  {label:>8s}: {cnt:3d} ({pct:5.2f}%)")

    return bins


def save_bin_csv(path, split_name, durations, bins):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["split", "bin", "count", "ratio_pct", "hours"]
        )
        writer.writeheader()
        n = len(durations)
        for lo, hi, label in bins:
            vals = [x for x in durations if lo <= x < hi]
            cnt = len(vals)
            ratio = (cnt / n * 100.0) if n > 0 else 0.0
            hours = sum(vals) / 3600.0
            writer.writerow(
                {
                    "split": split_name,
                    "bin": label,
                    "count": cnt,
                    "ratio_pct": f"{ratio:.3f}",
                    "hours": f"{hours:.6f}",
                }
            )


def main():
    parser = argparse.ArgumentParser(
        description="Duration distribution stats for one CSV"
    )
    parser.add_argument("--input-csv", required=True, help="Input subset CSV")
    parser.add_argument("--output-csv", required=True, help="Output bin stats CSV")
    parser.add_argument(
        "--name",
        default=None,
        help="Optional name for logs/output; defaults to input filename stem",
    )
    args = parser.parse_args()

    _, durations, speakers = load_durations(args.input_csv)
    name = args.name or Path(args.input_csv).stem
    bins = print_stats(name, durations, speakers)

    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    save_bin_csv(args.output_csv, name, durations, bins)
    print(f"\nSaved bin stats: {args.output_csv}")


if __name__ == "__main__":
    main()
