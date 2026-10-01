#!/usr/bin/env python3
"""
Track 2 submission rejection check. A submission is rejected if either rule
fails (official policy applies rule 1 on Test1, rule 2 on Test1 and Test2):

1. Early first-word emission: on more than --early-emission-threshold
   (default 5%) of streaming utterances, the first word has already settled
   to its final value before speech begins, i.e.
       first_stable_partial_time < audio_send_start_time + mfa_speech_start
   (TTFT-stable < 0). first_stable_partial_time is the same anchor as
   TTFT-stable (utils/compute_latency.py's _stable_partial_time, reused here,
   not reimplemented). A word cannot be recognized before it is spoken, so
   this indicates the first word was guessed rather than recognized.

2. Pass 1 / Pass 2 consistency: CER/WER are scored on Pass 1 (batch,
   <split>.predict.csv) and latency on Pass 2 (streaming,
   <split>.partial_results.json), so for every utterance in Pass 2 the
   Pass 2 final text (last "final_visible" event) must equal the Pass 1
   final text after hypothesis normalization (utils/normalize_hyp.py's
   normalize_text, same as official scoring). Any mismatch, or a Pass 2
   utterance missing from Pass 1, fails this rule.

Usage:
    python3 track2_reject_check.py --partial-json Test1.partial_results.json \
        --manifest-csv manifest/Test1_streaming.csv \
        --predict-csv Test1.predict.csv \
        [--mfa-col mfa_speech_start] [--hyp-col raw_hypos] \
        [--early-emission-threshold 0.05] [--out-json out.json]
"""
import argparse
import csv
import json
import os
import sys
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compute_latency import _extract_text_events, _load_mfa_start_map, _stable_partial_time
from normalize_hyp import normalize_text

DEFAULT_EARLY_EMISSION_THRESHOLD = 0.05


def compute_early_emission_rate(
    partial_json_path: str,
    manifest_csv: str,
    mfa_col: str = "mfa_speech_start",
) -> Dict[str, object]:
    """Fraction of utterances whose first word settled before speech onset.
    Same utterance set as compute_latency's ttft_stable_sec."""
    with open(partial_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mfa_start_map = _load_mfa_start_map(manifest_csv, mfa_col)

    n_checked = 0
    n_early = 0
    for uid, record in data.items():
        if not isinstance(record, dict) or "timing" not in record:
            continue
        mfa_start = mfa_start_map.get(uid)
        if mfa_start is None:
            continue
        t_stable = _stable_partial_time(_extract_text_events(record))
        if t_stable is None:
            continue
        n_checked += 1
        if t_stable < float(record["timing"]["audio_send_start_time"]) + mfa_start:
            n_early += 1

    return {
        "n_utts_checked": n_checked,
        "n_utts_early": n_early,
        "early_emission_rate": (n_early / n_checked) if n_checked else None,
    }


def _pass2_final_text(record: object) -> Optional[str]:
    """Text of the last final_visible event, or None if there is none."""
    if not isinstance(record, dict):
        return None
    finals = [
        e for e in record.get("events", [])
        if isinstance(e, dict) and e.get("event") == "final_visible"
    ]
    return str(finals[-1].get("text") or "") if finals else None


def compare_passes(
    partial_json_path: str,
    predict_csv: str,
    hyp_col: str = "raw_hypos",
) -> Dict[str, object]:
    """Compare Pass 2 final_visible text with Pass 1 predict.csv text,
    after hypothesis normalization, for every utterance in Pass 2."""
    with open(partial_json_path, "r", encoding="utf-8") as f:
        pass2 = json.load(f)
    with open(predict_csv, "r", encoding="utf-8", newline="") as f:
        pass1 = {row["id"]: row.get(hyp_col) or "" for row in csv.DictReader(f)}

    n_compared = 0
    n_missing = 0
    n_mismatch = 0
    for uid, record in pass2.items():
        text2 = _pass2_final_text(record)
        if text2 is None or uid not in pass1:
            n_missing += 1
            continue
        n_compared += 1
        if normalize_text(pass1[uid]).split() != normalize_text(text2).split():
            n_mismatch += 1

    return {
        "n_utts_compared": n_compared,
        "n_utts_missing": n_missing,
        "n_utts_mismatch": n_mismatch,
        "final_match_rate": ((n_compared - n_mismatch) / n_compared) if n_compared else None,
    }


def check_submission(
    partial_json_path: str,
    manifest_csv: str,
    predict_csv: str,
    mfa_col: str = "mfa_speech_start",
    hyp_col: str = "raw_hypos",
    early_emission_threshold: float = DEFAULT_EARLY_EMISSION_THRESHOLD,
) -> Dict[str, object]:
    early = compute_early_emission_rate(partial_json_path, manifest_csv, mfa_col)
    passes = compare_passes(partial_json_path, predict_csv, hyp_col)

    reasons = []
    rate = early["early_emission_rate"]
    if rate is not None and rate > early_emission_threshold:
        reasons.append(
            f"early first-word emission: {rate:.4f} > {early_emission_threshold:.4f}"
        )
    if passes["n_utts_mismatch"] or passes["n_utts_missing"]:
        reasons.append(
            f"Pass 1 / Pass 2 inconsistent: {passes['n_utts_mismatch']} mismatched, "
            f"{passes['n_utts_missing']} missing"
        )

    return {
        "early_emission": early,
        "early_emission_threshold": early_emission_threshold,
        "pass_consistency": passes,
        "rejected": bool(reasons),
        "reasons": reasons,
    }


def get_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--partial-json", required=True, help="Path to <split>.partial_results.json (Pass 2)")
    p.add_argument("--manifest-csv", required=True, help="Streaming manifest CSV with 'id' and the MFA start-time column")
    p.add_argument("--predict-csv", required=True, help="Path to <split>.predict.csv (Pass 1)")
    p.add_argument("--mfa-col", default="mfa_speech_start", help="Manifest column for MFA speech start (seconds)")
    p.add_argument("--hyp-col", default="raw_hypos", help="Hypothesis column in --predict-csv")
    p.add_argument(
        "--early-emission-threshold",
        type=float,
        default=DEFAULT_EARLY_EMISSION_THRESHOLD,
        help="Reject when early_emission_rate is above this (default: 0.05)",
    )
    p.add_argument("--out-json", default=None, help="Optional output path to save the result")
    return p


def main():
    args = get_parser().parse_args()
    result = check_submission(
        args.partial_json,
        args.manifest_csv,
        args.predict_csv,
        mfa_col=args.mfa_col,
        hyp_col=args.hyp_col,
        early_emission_threshold=args.early_emission_threshold,
    )
    print(json.dumps(result, indent=2))
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Track 2 rejection check written to: {args.out_json}")


if __name__ == "__main__":
    main()
