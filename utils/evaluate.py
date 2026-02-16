#!/usr/bin/env python3
"""
ASR Evaluation – same pipeline as scoring.py, without Codabench API.

Pipeline:
  1. Load predictions from hyp CSV (id, raw_hypos)
  2. Normalize hypothesis text (EnglishTextNormalizer, apply_markup=False)
  3. sclite alignment (ref1 vs hyp, ref2 vs hyp)
  4. Compute min-two-refs WER / CER from SGML (with UNK handling)
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

from normalize_hyp import normalize_text


def get_parser():
    p = argparse.ArgumentParser(
        description="ASR evaluation (same logic as scoring.py, without Codabench API)"
    )
    p.add_argument("--split", required=True, help="Split name (e.g. Dev-all, test1)")
    p.add_argument(
        "--hyp-csv",
        required=True,
        help="CSV with hypothesis predictions (must have 'id' column)",
    )
    p.add_argument(
        "--hyp-col",
        default="raw_hypos",
        help="Hypothesis column name (default: raw_hypos)",
    )
    p.add_argument(
        "--manifest-csv",
        required=True,
        help="Manifest CSV with 'id' column (defines utterance order)",
    )
    p.add_argument(
        "--ref-dir", required=True, help="Directory with pre-computed ref .trn files"
    )
    p.add_argument("--eval-dir", required=True, help="Output / working directory")
    p.add_argument(
        "--out-json",
        default=None,
        help="Output JSON path (default: eval-dir/metrics.SPLIT.json)",
    )
    return p


# ====================================================================
# I/O helpers
# ====================================================================


def load_manifest_ids(csv_path: str) -> List[str]:
    """Read manifest CSV and return ordered list of IDs."""
    ids = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.append(row["id"])
    return ids


def load_predictions(csv_path: str, hyp_col: str) -> Dict[str, str]:
    """Load predictions (id -> raw_hyp_text) from CSV file."""
    preds = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["id"]
            text = row.get(hyp_col, "")
            preds[uid] = text
    return preds


def write_trn(texts: List[str], ids: List[str], path: str):
    """Write text + uttid to TRN file."""
    with open(path, "w", encoding="utf-8") as f:
        for text, uid in zip(texts, ids):
            f.write(f"{text} ({uid})\n")


# ====================================================================
# sclite runner
# ====================================================================


def run_sclite(ref_trn: str, hyp_trn: str, sgml_out: str) -> bool:
    """
    Run sclite alignment: ref vs hyp -> SGML.
    Returns True on success.
    """
    try:
        result = subprocess.run(
            [
                "sclite",
                "-r",
                ref_trn,
                "trn",
                "-h",
                hyp_trn,
                "trn",
                "-i",
                "wsj",
                "-o",
                "all",
                "sgml",
            ],
            capture_output=True,
            timeout=600,
        )
        # sclite writes <hyp_trn>.sgml
        generated_sgml = hyp_trn + ".sgml"
        if os.path.isfile(generated_sgml):
            shutil.move(generated_sgml, sgml_out)
            # Cleanup other sclite artifacts
            for ext in [".sys", ".raw", ".pra"]:
                artifact = hyp_trn + ext
                if os.path.isfile(artifact):
                    os.remove(artifact)
            return True
        return False
    except Exception as e:
        print(f"sclite error: {e}")
        return False


# ====================================================================
# Main scoring
# ====================================================================


def score_split_with_sclite(
    split: str,
    manifest_ids: List[str],
    hyp_normalized: List[str],
    reference_dir: str,
    WORK_DIR: str,
) -> Optional[dict]:
    """Score a split using sclite alignment + SGML parsing."""
    from compute_metrics import compute_from_sgml

    SCTK_DIR = os.path.join(WORK_DIR, "sctk")
    os.makedirs(SCTK_DIR, exist_ok=True)

    # Sequential utt IDs matching pre-computed ref .trn files
    utt_ids = [f"utt{i:06d}" for i in range(1, len(manifest_ids) + 1)]

    # Write normalized hyp to .trn
    hyp_trn = os.path.join(WORK_DIR, f"hyp.{split}.norm.trn")
    write_trn(hyp_normalized, utt_ids, hyp_trn)

    # Pre-computed ref .trn files (in reference directory)
    ref1_trn = os.path.join(reference_dir, f"ref1.{split}.norm.trn")
    ref2_trn = os.path.join(reference_dir, f"ref2.{split}.norm.trn")

    if not os.path.isfile(ref1_trn) or not os.path.isfile(ref2_trn):
        print(f"WARNING: Pre-normalized ref .trn files not found for {split}")
        return None

    # Run sclite
    sgml1 = os.path.join(SCTK_DIR, f"{split}.ref1.sgml")
    sgml2 = os.path.join(SCTK_DIR, f"{split}.ref2.sgml")

    # Need separate hyp copies for each sclite run (sclite writes <hyp>.sgml)
    hyp_trn_1 = os.path.join(WORK_DIR, f"hyp.{split}.ref1.norm.trn")
    hyp_trn_2 = os.path.join(WORK_DIR, f"hyp.{split}.ref2.norm.trn")
    shutil.copy2(hyp_trn, hyp_trn_1)
    shutil.copy2(hyp_trn, hyp_trn_2)

    ok1 = run_sclite(ref1_trn, hyp_trn_1, sgml1)
    ok2 = run_sclite(ref2_trn, hyp_trn_2, sgml2)

    if not ok1 or not ok2:
        print(f"WARNING: sclite alignment failed for {split}")
        return None

    return compute_from_sgml(sgml1, sgml2)


def main():
    args = get_parser().parse_args()

    split = args.split
    reference_dir = args.ref_dir
    WORK_DIR = args.eval_dir

    os.makedirs(WORK_DIR, exist_ok=True)

    out_json = args.out_json or os.path.join(WORK_DIR, f"metrics.{split}.json")

    print(f"sclite: {shutil.which('sclite')}")

    print(f"\n--- Scoring split: {split} ---")

    # 1) Load predictions
    preds = load_predictions(args.hyp_csv, args.hyp_col)
    print(f"Loaded {len(preds)} predictions")

    # 2) Load manifest to get ordered IDs
    manifest_ids = load_manifest_ids(args.manifest_csv)
    print(f"Manifest has {len(manifest_ids)} entries")

    # 3) Match & normalize hypothesis
    matched = 0
    hyp_normalized = []
    for uid in manifest_ids:
        raw_hyp = preds.get(uid, "")
        if uid in preds:
            matched += 1
        hyp_normalized.append(normalize_text(raw_hyp))
    print(f"Matched {matched} / {len(manifest_ids)} predictions")

    # 4) Score via sclite
    result = score_split_with_sclite(
        split, manifest_ids, hyp_normalized, reference_dir, WORK_DIR
    )

    if result is None:
        print(f"ERROR: sclite scoring failed for split {split}")
        sys.exit(1)

    wer = result["wer"]
    cer = result["cer"]
    n_utts = result["n_utts"]
    print(f"#utts: {n_utts}")
    print(f"WER: {wer:.4f}  ({wer*100:.2f}%)")
    print(f"CER: {cer:.4f}  ({cer*100:.2f}%)")

    # Save
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Written to: {out_json}")


if __name__ == "__main__":
    main()
