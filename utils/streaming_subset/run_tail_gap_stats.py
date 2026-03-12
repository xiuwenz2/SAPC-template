#!/usr/bin/env python3
"""
Analyze tail gap on filtered samples:
    tail_gap = duration - vad_speech_end
Outputs ranked rows and filtered rows.
"""

import argparse
import csv


def load_by_id(path):
    with open(path, "r", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    idx = int(len(sorted_vals) * p)
    if idx >= len(sorted_vals):
        idx = len(sorted_vals) - 1
    return sorted_vals[idx]


def dataset_stats(rows):
    speakers = {r.get("speaker", "") for r in rows if r.get("speaker", "")}
    total_duration = sum(safe_float(r.get("duration", 0.0)) for r in rows)
    return len(speakers), len(rows), total_duration


def main():
    parser = argparse.ArgumentParser(description="Tail-gap stats for filtered samples")
    parser.add_argument(
        "--input-filtered-csv", required=True, help="Filtered CSV from previous step"
    )
    parser.add_argument("--vad-csv", required=True, help="VAD CSV (*_vad.csv)")
    parser.add_argument(
        "--output-csv", required=True, help="Output ranked tail-gap CSV"
    )
    parser.add_argument(
        "--output-filtered-csv", required=True, help="Output filtered CSV"
    )
    parser.add_argument(
        "--min-gap", type=float, default=0.5, help="Minimum kept tail gap (seconds)"
    )
    parser.add_argument(
        "--max-gap", type=float, default=1.5, help="Maximum kept tail gap (seconds)"
    )
    args = parser.parse_args()

    kept = load_by_id(args.input_filtered_csv)
    vad = load_by_id(args.vad_csv)

    common_ids = sorted(set(kept.keys()) & set(vad.keys()))
    rows = []
    gaps = []

    kept_rows = []
    for uid in common_ids:
        k = kept[uid]
        v = vad[uid]
        duration = safe_float(k.get("duration", 0.0))
        vad_end = safe_float(v.get("speech_end", 0.0))
        gap = duration - vad_end
        # Guard against tiny negative floating-point noise.
        if gap < 0 and abs(gap) < 1e-3:
            gap = 0.0
        gaps.append(gap)

        out = dict(k)
        out["vad_speech_end"] = round(vad_end, 3)
        out["audio_end"] = round(duration, 3)
        out["tail_gap"] = round(gap, 3)
        rows.append(out)
        if args.min_gap <= gap <= args.max_gap:
            kept_rows.append(k)

    rows.sort(key=lambda r: safe_float(r["tail_gap"]), reverse=True)

    if rows:
        fields = list(rows[0].keys())
        with open(args.output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    if kept_rows:
        with open(args.output_filtered_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(kept_rows[0].keys()))
            writer.writeheader()
            writer.writerows(kept_rows)
    else:
        with open(args.output_filtered_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id"])

    if not gaps:
        print("No common rows to analyze.")
        return

    gaps_sorted = sorted(gaps)
    n = len(gaps_sorted)
    mean = sum(gaps_sorted) / n

    print(f"Input filtered CSV:  {args.input_filtered_csv}")
    print(f"VAD CSV:      {args.vad_csv}")
    print(f"Ranked CSV:          {args.output_csv}")
    print(f"Output filtered CSV: {args.output_filtered_csv}")
    print(f"Keep range:   [{args.min_gap:.3f}, {args.max_gap:.3f}]s")
    print(f"Samples:      {n}")
    print(f"Mean gap:     {mean:.3f}s")
    print(f"P10:          {percentile(gaps_sorted, 0.10):.3f}s")
    print(f"P25:          {percentile(gaps_sorted, 0.25):.3f}s")
    print(f"P50:          {percentile(gaps_sorted, 0.50):.3f}s")
    print(f"P75:          {percentile(gaps_sorted, 0.75):.3f}s")
    print(f"P90:          {percentile(gaps_sorted, 0.90):.3f}s")
    print(f"P95:          {percentile(gaps_sorted, 0.95):.3f}s")
    print(f"P99:          {percentile(gaps_sorted, 0.99):.3f}s")

    bins = [
        (0.0, 0.1, "0-0.1s"),
        (0.1, 0.3, "0.1-0.3s"),
        (0.3, 0.5, "0.3-0.5s"),
        (0.5, 1.0, "0.5-1.0s"),
        (1.0, 2.0, "1.0-2.0s"),
        (2.0, 3.0, "2.0-3.0s"),
        (3.0, 1e9, "3.0s+"),
    ]
    print("\nGap distribution:")
    for lo, hi, label in bins:
        count = sum(1 for g in gaps_sorted if lo <= g < hi)
        pct = count / n * 100
        print(f"  {label:>8s}: {count:5d} ({pct:5.2f}%)")
    keep_n = len(kept_rows)
    keep_ratio = keep_n / n * 100
    print(f"\nKept rows:    {keep_n} ({keep_ratio:.2f}%)")
    print(f"Filtered out: {n - keep_n} ({100 - keep_ratio:.2f}%)")

    in_spk, in_files, in_dur = dataset_stats(list(kept.values()))
    out_spk, out_files, out_dur = dataset_stats(kept_rows)
    print("\nDataset info (before -> after this step):")
    print(f"  speakers:    {in_spk} -> {out_spk}")
    print(f"  files:       {in_files} -> {out_files}")
    print(f"  duration(h): {in_dur / 3600:.2f} -> {out_dur / 3600:.2f}")


if __name__ == "__main__":
    main()
