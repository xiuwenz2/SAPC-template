#!/usr/bin/env python3
import argparse
import json
import os
import sys
import re
from typing import Dict, List, Tuple

from metrics.cer import CharErrorRateMinTwoRefs
from metrics.wer import WordErrorRateMinTwoRefs


def parse_sgml_csdi(
    path: str,
    process_unk: bool = True,
    unk_token: str = "unk",
) -> tuple[list[str], list[str]]:
    """
    Parse PATH-style SGML files, such as:

      <PATH id="(utt000001)" word_cnt="12" sequence="0">
      S,"miss","ms":C,"hobson","hobson":I,,"it":D,"word",""
      </PATH>

    Each segment looks like:
      C,"ref","hyp"
      S,"ref","hyp"
      D,"ref",""
      I,,"hyp"

    Returns:
      preds  : ["hyp tokens...", ...]
      target : ["ref tokens...", ...]

    If process_unk=True, apply UNK handling:
      - S and ref == UNK  : replace ref UNK with the corresponding hyp token
      - D and ref == UNK  : drop this UNK from target
      - I and hyp == UNK  : drop this UNK from preds
    """
    preds: List[str] = []
    target: List[str] = []

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("<PATH"):
            # utt_id is currently only used for debugging, not as a key
            m = re.search(r'id="([^"]+)"', line)
            if not m:
                i += 1
                continue
            utt_id = m.group(1)
            if utt_id.startswith("(") and utt_id.endswith(")"):
                utt_id = utt_id[1:-1]

            # Next non-empty, non-tag line is the alignment line
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("<")):
                j += 1
            if j >= len(lines):
                break
            align_line = lines[j].strip()

            ref_tokens: List[str] = []
            hyp_tokens: List[str] = []

            # Split by ':' into alignment segments
            segments = align_line.split(":")
            for seg in segments:
                seg = seg.strip()
                if not seg:
                    continue
                op = seg[0]
                # Remove the leading letter and comma: "C,", "S,", "D,", "I,"
                rest = seg[2:]  # e.g. "\"miss\",\"ms\"" or "\"word\",\"\"" or ",\"it\""

                # Simple split by comma (assuming no commas inside tokens)
                parts = [p.strip() for p in rest.split(",")]

                def strip_q(x: str) -> str:
                    x = x.strip()
                    if len(x) >= 2 and x[0] == '"' and x[-1] == '"':
                        return x[1:-1]
                    return x

                if op in ("C", "S"):
                    # Format: "ref","hyp"
                    if len(parts) >= 2:
                        ref_tok = strip_q(parts[0])
                        hyp_tok = strip_q(parts[1])
                    else:
                        ref_tok = ""
                        hyp_tok = ""

                    # UNK rule: if S and ref is UNK, replace ref UNK with hyp token
                    if process_unk and op == "S" and ref_tok == unk_token and hyp_tok:
                        ref_tok = hyp_tok

                    if ref_tok:
                        ref_tokens.append(ref_tok)
                    if hyp_tok:
                        hyp_tokens.append(hyp_tok)

                elif op == "D":
                    # Format: "ref",""
                    if len(parts) >= 1:
                        ref_tok = strip_q(parts[0])
                    else:
                        ref_tok = ""

                    # UNK rule: if D and ref is UNK, drop this UNK
                    if process_unk and ref_tok == unk_token:
                        ref_tok = ""

                    if ref_tok:
                        ref_tokens.append(ref_tok)
                    # hyp is empty, nothing added

                elif op == "I":
                    # Format: ,"hyp"  => parts[0] may be empty, parts[1] is "hyp"
                    hyp_tok = ""
                    if len(parts) == 1:
                        hyp_tok = strip_q(parts[0])
                    elif len(parts) >= 2:
                        hyp_tok = strip_q(parts[1])

                    # UNK rule: if I and hyp is UNK, drop this UNK
                    if process_unk and hyp_tok == unk_token:
                        hyp_tok = ""

                    if hyp_tok:
                        hyp_tokens.append(hyp_tok)

                # other ops are ignored

            preds.append(" ".join(hyp_tokens))
            target.append(" ".join(ref_tokens))
            i = j  # jump to the alignment line
        i += 1

    if not preds:
        raise RuntimeError(f"No PATH alignment found in SGML: {path}")

    return preds, target


# ---------- API ----------

def compute_from_sgml(sgml_ref1: str, sgml_ref2: str):
    """
    Compute min-two-refs WER/CER from two SGML files.
    Called by scoring.py (bundle) or directly as a library function.
    """
    preds_ref1, target_ref1 = parse_sgml_csdi(sgml_ref1, process_unk=True, unk_token="unk")
    preds_ref2, target_ref2 = parse_sgml_csdi(sgml_ref2, process_unk=True, unk_token="unk")

    if preds_ref1 != preds_ref2:
        print("ERROR: preds from sgml-ref1 and sgml-ref2 are not identical!", file=sys.stderr)
        print(f"  len(preds_ref1) = {len(preds_ref1)}, len(preds_ref2) = {len(preds_ref2)}", file=sys.stderr)
        sys.exit(1)

    preds = preds_ref1

    cer_metric = CharErrorRateMinTwoRefs(clip_at_one=True)
    wer_metric = WordErrorRateMinTwoRefs(clip_at_one=True)

    cer_min = float(cer_metric(preds, target_ref1, target_ref2))
    wer_min = float(wer_metric(preds, target_ref1, target_ref2))

    return {
        "n_utts": len(preds),
        "wer": wer_min,
        "cer": cer_min,
    }


# ---------- CLI ----------

def get_parser():
    p = argparse.ArgumentParser(
        description="Stage3: reconstruct ref/hyp from SGML PATH alignment "
                    "and compute metrics (CharErrorRate / WordErrorRate)"
    )
    p.add_argument(
        "--sgml-ref1",
        required=True,
        help="sclite-generated SGML (ref1 alignment, with parentheses / markup)",
    )
    p.add_argument(
        "--sgml-ref2",
        required=True,
        help="sclite-generated SGML (ref2 alignment, no parentheses / official)",
    )
    p.add_argument(
        "--out-json",
        help="output JSON path for aggregated metrics (including ref1/ref2 and diffs)",
        default=None,
    )
    return p


def main():
    args = get_parser().parse_args()

    if not os.path.isfile(args.sgml_ref1):
        print(f"ERROR: sgml-ref1 file not found: {args.sgml_ref1}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.sgml_ref2):
        print(f"ERROR: sgml-ref2 file not found: {args.sgml_ref2}", file=sys.stderr)
        sys.exit(1)

    result = compute_from_sgml(args.sgml_ref1, args.sgml_ref2)

    summary = {
        "n_utts": result["n_utts"],
        "min_two_refs": {
            "cer": result["cer"],
            "wer": result["wer"],
            "sgml_ref1": os.path.abspath(args.sgml_ref1),
            "sgml_ref2": os.path.abspath(args.sgml_ref2),
        },
    }

    print("=== Stage3 metrics (min over ref1/ref2) ===")
    print(f"#utts              : {summary['n_utts']}")
    print(f"MIN CER / WER      : {result['cer']:.4f}  /  {result['wer']:.4f}")

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"[Stage3] Metrics JSON written to: {args.out_json}")


if __name__ == "__main__":
    main()
