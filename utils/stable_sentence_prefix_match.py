#!/usr/bin/env python3
"""
Stage 4 (streaming track only): stable_sentence_prefix_match_rate -- the
fraction of utterances where the word #0 a system's output locks onto by
its final answer (see utils/compute_latency.py's _stable_partial_time for
the exact lock-on definition -- reused here, not reimplemented) prefix-matches
the manifest reference's word #0 (--ref-col, default
norm_text_without_disfluency). A prefix match counts (a genuinely
truncated word like "wo" for "wow" shouldn't be penalized) -- this only
checks the start of the sentence, not the full transcript.

The hypothesis side is run through the same normalizer the rest of the
pipeline uses (normalize_hyp.normalize_text, i.e. EnglishTextNormalizer)
so the words being compared follow the same convention as official
WER/CER scoring.

Usage:
    python3 stable_sentence_prefix_match.py --partial-json <split>.partial_results.json \
        --manifest-csv manifest/Test1.csv \
        [--ref-col norm_text_without_disfluency] [--out-json out.json]
"""
import argparse
import csv
import json
import os
import sys
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compute_latency import _extract_text_events, _first_word
from normalize_hyp import normalize_text


def _load_ref_texts(manifest_csv: str, ref_col: str) -> Dict[str, str]:
    texts: Dict[str, str] = {}
    with open(manifest_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid = row.get("id")
            if uid:
                texts[uid] = (row.get(ref_col) or "").strip()
    return texts


def _is_prefix_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return a.startswith(b) or b.startswith(a)


def compute_stable_sentence_prefix_match_rate(
    partial_json_path: str,
    manifest_csv: str,
    ref_col: str = "norm_text_without_disfluency",
) -> Dict[str, object]:
    with open(partial_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ref_texts = _load_ref_texts(manifest_csv, ref_col)

    n_checked = 0
    n_match = 0

    for uid, record in data.items():
        ref_text = ref_texts.get(uid)
        if not ref_text:
            continue
        events = _extract_text_events(record)
        if not events:
            continue

        hyp_word = _first_word(normalize_text(events[-1][1]))
        ref_word = _first_word(ref_text)
        if hyp_word and ref_word:
            n_checked += 1
            if _is_prefix_match(hyp_word, ref_word):
                n_match += 1

    return {
        "n_utts_checked": n_checked,
        "stable_sentence_prefix_match_rate": (n_match / n_checked) if n_checked else None,
    }


def get_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--partial-json", required=True, help="Path to <split>.partial_results.json")
    p.add_argument("--manifest-csv", required=True, help="Manifest CSV with 'id' and the reference column")
    p.add_argument("--ref-col", default="norm_text_without_disfluency", help="Reference text column (default: norm_text_without_disfluency)")
    p.add_argument("--out-json", default=None, help="Optional output path to save the computed rate")
    return p


def main():
    args = get_parser().parse_args()
    result = compute_stable_sentence_prefix_match_rate(args.partial_json, args.manifest_csv, args.ref_col)
    print(json.dumps(result, indent=2))
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Stable sentence-prefix match summary written to: {args.out_json}")


if __name__ == "__main__":
    main()
