#!/usr/bin/env python3
"""
Rank and filter samples by FA (MFA) vs VAD boundary agreement.

Inputs:
  - FA CSV (e.g. subset_mfa.csv)
  - VAD CSV (e.g. subset_vad.csv)
Outputs:
  - ranked CSV: rows sorted by boundary mismatch score
  - filtered CSV: rows with |start_diff|<=thr and |end_diff|<=thr
"""

import argparse
import csv


def load_by_id(path):
    with open(path, "r", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["id"]: r for r in rows}


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def get_dataset_stats(rows):
    speakers = {r.get("speaker", "") for r in rows if r.get("speaker", "")}
    total_duration = sum(safe_float(r.get("duration", 0.0)) for r in rows)
    return len(speakers), total_duration


def main():
    parser = argparse.ArgumentParser(
        description="Filter samples by FA/VAD boundary diffs"
    )
    parser.add_argument("--fa-csv", required=True, help="FA CSV (e.g. *_mfa.csv)")
    parser.add_argument("--vad-csv", required=True, help="VAD CSV (e.g. *_vad.csv)")
    parser.add_argument("--base-csv", required=True, help="Base CSV (e.g. subset.csv)")
    parser.add_argument("--ranked-csv", required=True, help="Output ranked CSV")
    parser.add_argument("--filtered-csv", required=True, help="Output filtered CSV")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Boundary threshold in seconds (default: 0.1)",
    )
    args = parser.parse_args()

    fa = load_by_id(args.fa_csv)
    vad = load_by_id(args.vad_csv)
    base = load_by_id(args.base_csv)

    common_ids = sorted(set(fa.keys()) & set(vad.keys()) & set(base.keys()))
    ranked_rows = []
    kept_rows = []

    for uid in common_ids:
        fa_row = fa[uid]
        vad_row = vad[uid]
        base_row = dict(base[uid])

        fa_start = safe_float(fa_row.get("speech_start"))
        fa_end = safe_float(fa_row.get("speech_end"))
        vad_start = safe_float(vad_row.get("speech_start"))
        vad_end = safe_float(vad_row.get("speech_end"))

        start_diff = abs(fa_start - vad_start)
        end_diff = abs(fa_end - vad_end)
        score = start_diff + end_diff

        out = dict(base_row)
        out["fa_speech_start"] = round(fa_start, 3)
        out["fa_speech_end"] = round(fa_end, 3)
        out["vad_speech_start"] = round(vad_start, 3)
        out["vad_speech_end"] = round(vad_end, 3)
        out["start_diff_abs"] = round(start_diff, 3)
        out["end_diff_abs"] = round(end_diff, 3)
        out["match_score"] = round(score, 3)
        ranked_rows.append(out)

        if start_diff <= args.threshold and end_diff <= args.threshold:
            kept_rows.append(base_row)

    ranked_rows.sort(key=lambda r: safe_float(r["match_score"]))

    if ranked_rows:
        ranked_fields = list(ranked_rows[0].keys())
        with open(args.ranked_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ranked_fields)
            writer.writeheader()
            writer.writerows(ranked_rows)

    if kept_rows:
        kept_fields = list(kept_rows[0].keys())
        with open(args.filtered_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=kept_fields)
            writer.writeheader()
            writer.writerows(kept_rows)
    else:
        with open(args.filtered_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id"])

    total = len(common_ids)
    kept = len(kept_rows)
    ratio = (kept / total * 100.0) if total > 0 else 0.0
    ranked_speakers, ranked_total_dur = get_dataset_stats(ranked_rows)
    kept_speakers, kept_total_dur = get_dataset_stats(kept_rows)

    print(f"FA CSV:       {args.fa_csv}")
    print(f"VAD CSV:      {args.vad_csv}")
    print(f"Base CSV:     {args.base_csv}")
    print(f"Threshold:    {args.threshold:.3f}s")
    print(f"Common rows:  {total}")
    print(f"Kept rows:    {kept} ({ratio:.2f}%)")
    print(
        f"Ranked stats: speakers={ranked_speakers}, "
        f"total_duration={ranked_total_dur:.2f}s ({ranked_total_dur/3600:.2f}h)"
    )
    print(
        f"Kept stats:   speakers={kept_speakers}, "
        f"total_duration={kept_total_dur:.2f}s ({kept_total_dur/3600:.2f}h)"
    )
    print(f"Ranked CSV:   {args.ranked_csv}")
    print(f"Filtered CSV: {args.filtered_csv}")


if __name__ == "__main__":
    main()
