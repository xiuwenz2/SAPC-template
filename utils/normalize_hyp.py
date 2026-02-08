#!/usr/bin/env python3
"""
Normalize hypothesis text only: produce hyp .trn (and optionally add a column to CSV).
Uses apply_markup=False and optional token truncation (max words / max chars per token).
"""
import argparse
import csv
import os
import sys
from typing import List, Tuple

from tqdm import tqdm
from normalizer.text_normalizer_hf import EnglishTextNormalizer


def get_parser():
    p = argparse.ArgumentParser(
        description=(
            "Normalize hypothesis text: generate hyp.trn from a CSV column. "
            "Optionally add a norm_hyp column to CSV."
        )
    )
    p.add_argument("--csv", required=True, help="Input CSV, e.g. eval/dev.merged.csv")
    p.add_argument("--hyp-col", default="raw_hypos", help="Hypothesis column name (default: raw_hypos)")
    p.add_argument("--out-hyp", default=None, help="Output hyp.trn path.")
    p.add_argument(
        "--out-csv",
        default=None,
        help="Output CSV path: same rows with one extra column (default: norm_hyp). Use --out-hyp-col to set name.",
    )
    p.add_argument(
        "--out-hyp-col",
        default="norm_hyp",
        help="Name of the normalized hypothesis column when using --out-csv (default: norm_hyp).",
    )
    p.add_argument(
        "--max_hyp_words",
        type=int,
        default=512,
        help="Maximum number of words in hypothesis (default: 512).",
    )
    p.add_argument(
        "--max_hyp_token_chars",
        type=int,
        default=64,
        help="Maximum characters per hypothesis token; longer tokens truncated (default: 64).",
    )
    return p


def clamp_token_lengths(tokens: List[str], max_chars: int) -> Tuple[List[str], bool]:
    """Limit the maximum length of each token; return (new_token_list, truncated_flag)."""
    if max_chars <= 0:
        return tokens, False
    changed = False
    new_tokens: List[str] = []
    for t in tokens:
        if len(t) > max_chars:
            new_tokens.append(t[:max_chars])
            changed = True
        else:
            new_tokens.append(t)
    return new_tokens, changed


# ---------- API ----------

_normalizer = None


def normalize_text(
    text: str,
    max_hyp_words: int = 512,
    max_hyp_token_chars: int = 64,
) -> str:
    """
    Normalize a single hypothesis string.
    Called by scoring.py (bundle) or directly as a library function.
    """
    global _normalizer
    if _normalizer is None:
        _normalizer = EnglishTextNormalizer()

    norm = _normalizer.norm(text, apply_markup=False)
    tokens = norm.split()
    if len(tokens) > max_hyp_words:
        tokens = tokens[:max_hyp_words]
    tokens, _ = clamp_token_lengths(tokens, max_hyp_token_chars)
    return " ".join(tokens)


# ---------- CLI ----------


def main():
    args = get_parser().parse_args()

    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    out_csv_mode = bool(args.out_csv)
    out_trn_mode = bool(args.out_hyp)
    if not out_csv_mode and not out_trn_mode:
        print("ERROR: set either --out-csv or --out-hyp", file=sys.stderr)
        sys.exit(1)

    csv_rows: List[dict] = []
    csv_fieldnames: List[str] = []

    f_hyp = None
    if out_trn_mode:
        f_hyp = open(args.out_hyp, "w", encoding="utf-8")

    with open(args.csv, "r", encoding="utf-8") as f_csv:
        reader = csv.DictReader(f_csv)
        if args.hyp_col not in reader.fieldnames:
            print(f"ERROR: hyp-col '{args.hyp_col}' not in CSV header: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)

        if out_csv_mode:
            csv_fieldnames = list(reader.fieldnames) + [args.out_hyp_col]

        try:
            num_rows = 0
            for idx, row in tqdm(enumerate(reader, start=1), desc="Normalizing hyps"):
                raw_hyp = row.get(args.hyp_col, "") or ""

                norm_hyp = normalize_text(
                    raw_hyp,
                    max_hyp_words=args.max_hyp_words,
                    max_hyp_token_chars=args.max_hyp_token_chars,
                )

                if out_csv_mode:
                    row[args.out_hyp_col] = norm_hyp
                    csv_rows.append(row)

                if out_trn_mode:
                    utt_id = f"utt{idx:06d}"
                    f_hyp.write(f"{norm_hyp} ({utt_id})\n")

                num_rows += 1
        finally:
            if f_hyp is not None:
                f_hyp.close()

    if out_csv_mode and csv_rows:
        out_dir = os.path.dirname(args.out_csv)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=csv_fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"[normalize_hyp] Wrote CSV with column '{args.out_hyp_col}': {args.out_csv} (rows={len(csv_rows)})")

    if out_trn_mode:
        print(f"[normalize_hyp] Done. rows={num_rows}")
        print(f"  hyp.trn -> {args.out_hyp}")


if __name__ == "__main__":
    main()
