#!/usr/bin/env python3
"""
Normalize reference text only: produce ref1 (with disfluency) and ref2 (without disfluency).
Reads CSV with a reference column; optionally writes ref1/ref2 .trn files and/or
adds norm_text_with_disfluency and norm_text_without_disfluency columns to CSV.
"""
import argparse
import csv
import os
import sys
from typing import List

from tqdm import tqdm
from normalizer.text_normalizer_hf import EnglishTextNormalizer


def get_parser():
    p = argparse.ArgumentParser(
        description=(
            "Normalize reference text: generate ref1 (with disfluency) and ref2 (without disfluency) "
            "from a CSV column. Output .trn files and/or add columns to CSV."
        )
    )
    p.add_argument(
        "--csv",
        required=True,
        help="Input CSV, e.g. eval/dev.csv or manifest/Train.csv",
    )
    p.add_argument(
        "--ref-col",
        default="raw_trans",
        help="Reference column name (default: raw_trans). Use 'text' for manifest CSV.",
    )
    p.add_argument(
        "--out-ref1",
        default=None,
        help="Output ref1.trn path (keep parentheses / with disfluency).",
    )
    p.add_argument(
        "--out-ref2",
        default=None,
        help="Output ref2.trn path (remove parentheses / without disfluency).",
    )
    p.add_argument(
        "--out-csv",
        default=None,
        help="Output CSV path: same rows with two extra columns "
        "norm_text_with_disfluency (ref1) and norm_text_without_disfluency (ref2).",
    )
    return p


def main():
    args = get_parser().parse_args()

    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    out_csv_mode = bool(args.out_csv)
    out_trn_mode = bool(args.out_ref1 and args.out_ref2)
    if not out_csv_mode and not out_trn_mode:
        print(
            "ERROR: set either --out-csv or both --out-ref1 and --out-ref2",
            file=sys.stderr,
        )
        sys.exit(1)

    normalizer = EnglishTextNormalizer()
    csv_rows: List[dict] = []
    csv_fieldnames: List[str] = []

    def open_ref_files():
        if out_trn_mode:
            return open(args.out_ref1, "w", encoding="utf-8"), open(
                args.out_ref2, "w", encoding="utf-8"
            )
        return None, None

    with open(args.csv, "r", encoding="utf-8") as f_csv:
        reader = csv.DictReader(f_csv)
        if args.ref_col not in reader.fieldnames:
            print(
                f"ERROR: ref-col '{args.ref_col}' not in CSV header: {reader.fieldnames}",
                file=sys.stderr,
            )
            sys.exit(1)

        if out_csv_mode:
            csv_fieldnames = list(reader.fieldnames) + [
                "norm_text_with_disfluency",
                "norm_text_without_disfluency",
            ]

        f_ref1, f_ref2 = open_ref_files()
        try:
            num_rows = 0
            for idx, row in tqdm(enumerate(reader, start=1), desc="Normalizing refs"):
                raw_ref = row.get(args.ref_col, "") or ""

                norm_ref1 = normalizer.norm(
                    raw_ref,
                    apply_markup=True,
                    remove_parentheses=False,
                )
                norm_ref2 = normalizer.norm(
                    raw_ref,
                    apply_markup=True,
                    remove_parentheses=True,
                )

                if out_csv_mode:
                    row["norm_text_with_disfluency"] = norm_ref1
                    row["norm_text_without_disfluency"] = norm_ref2
                    csv_rows.append(row)

                if out_trn_mode:
                    utt_id = f"utt{idx:06d}"
                    f_ref1.write(f"{norm_ref1} ({utt_id})\n")
                    f_ref2.write(f"{norm_ref2} ({utt_id})\n")

                num_rows += 1
        finally:
            if f_ref1 is not None:
                f_ref1.close()
            if f_ref2 is not None:
                f_ref2.close()

    if out_csv_mode and csv_rows:
        out_dir = os.path.dirname(args.out_csv)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f_out:
            writer = csv.DictWriter(
                f_out, fieldnames=csv_fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(csv_rows)
        print(
            f"[normalize_ref] Wrote CSV with norm columns: {args.out_csv} (rows={len(csv_rows)})"
        )

    if out_trn_mode:
        print(f"[normalize_ref] Done. rows={num_rows}")
        print(f"  ref1.trn -> {args.out_ref1}")
        print(f"  ref2.trn -> {args.out_ref2}")


if __name__ == "__main__":
    main()
