#!/usr/bin/env python3
"""
Compute streaming latency metrics from *.partial_results.json.

Expected per-utterance structure (new format):
{
  "events": [...],
  "timing": {
    "audio_send_start_time": ...,
    "first_partial_time": ...,
    "audio_end_oracle_time": ...,
    "final_visible_time": ...
  }
}

Metrics:
  TTFT = first_partial_time - audio_send_start_time
  TTLT = final_visible_time - audio_end_oracle_time
"""

import argparse
import csv
import json
from typing import Dict, List, Optional, Tuple

Timing = Dict[str, float]
Event = Tuple[float, str]


def _percentile(values: List[float], q: float) -> Optional[float]:
    """q in [0, 100]. Linear interpolation percentile."""
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    rank = (q / 100.0) * (len(xs) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(xs) - 1)
    frac = rank - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def _summary(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {
            "count": 0,
            "median": None,
            "p50": None,
            "p90": None,
            "p95": None,
        }
    return {
        "count": len(values),
        "median": _percentile(values, 50.0),
        "p50": _percentile(values, 50.0),
        "p90": _percentile(values, 90.0),
        "p95": _percentile(values, 95.0),
    }


def _load_mfa_start_map(manifest_csv: str, mfa_col: str) -> Dict[str, float]:
    starts: Dict[str, float] = {}
    with open(manifest_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row.get("id")
            if not uid:
                continue
            try:
                starts[uid] = float(row[mfa_col])
            except (KeyError, TypeError, ValueError):
                continue
    return starts


def _extract_text_events(record: object) -> List[Event]:
    events: List[Event] = []
    if not isinstance(record, dict):
        return events
    for item in record.get("events", []):
        if not isinstance(item, dict):
            continue
        ts = item.get("time")
        if ts is None:
            continue
        events.append((float(ts), str(item.get("text", ""))))
    return events


def _first_non_empty_or_last_event_time(record: object) -> Optional[float]:
    events = _extract_text_events(record)
    if not events:
        return None
    for ts, txt in events:
        if txt.strip() != "":
            return ts
    # If all empty, fall back to the last partial/event timestamp.
    return events[-1][0]


def compute_latency_from_partial_json(
    path: str,
    manifest_csv: Optional[str] = None,
    mfa_col: str = "mfa_speech_start",
) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mfa_start_map: Dict[str, float] = {}
    if manifest_csv:
        mfa_start_map = _load_mfa_start_map(manifest_csv, mfa_col)

    ttft_values: List[float] = []
    ttlt_values: List[float] = []
    n_total = 0
    n_with_timing = 0
    n_with_mfa = 0

    for uid, record in data.items():
        n_total += 1
        if not isinstance(record, dict) or "timing" not in record:
            continue
        timing: Timing = record["timing"]
        n_with_timing += 1

        t_audio_start = float(timing["audio_send_start_time"])
        t_first_non_empty = _first_non_empty_or_last_event_time(record)
        t_audio_end_oracle = float(timing["audio_end_oracle_time"])
        t_final_visible = float(timing["final_visible_time"])

        mfa_start = mfa_start_map.get(uid)
        if mfa_start is not None:
            n_with_mfa += 1
        if (
            t_audio_start is not None
            and t_first_non_empty is not None
            and mfa_start is not None
        ):
            true_speech_start_abs = t_audio_start + mfa_start
            ttft = t_first_non_empty - true_speech_start_abs
            ttft_values.append(ttft)

        if t_audio_end_oracle is not None and t_final_visible is not None:
            ttlt = t_final_visible - t_audio_end_oracle
            if ttlt >= 0.0:
                ttlt_values.append(ttlt)

    return {
        "n_utts_total": n_total,
        "n_utts_with_timing": n_with_timing,
        "n_utts_with_mfa_start": n_with_mfa,
        "ttft_definition": "first_non_empty_partial_or_last - (audio_send_start + mfa_speech_start)",
        "ttlt_definition": "final_visible - audio_end_oracle",
        "ttft_sec": _summary(ttft_values),
        "ttlt_sec": _summary(ttlt_values),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute TTFT/TTLT metrics from partial_results JSON."
    )
    parser.add_argument(
        "--partial-json",
        required=True,
        help="Path to <split>.partial_results.json",
    )
    parser.add_argument(
        "--out-json",
        default=None,
        help="Optional output path to save computed latency summary.",
    )
    parser.add_argument(
        "--manifest-csv",
        default=None,
        help="Optional manifest CSV containing id and mfa_speech_start column.",
    )
    parser.add_argument(
        "--mfa-col",
        default="mfa_speech_start",
        help="Column name for MFA speech start (seconds).",
    )
    args = parser.parse_args()

    result = compute_latency_from_partial_json(
        args.partial_json,
        manifest_csv=args.manifest_csv,
        mfa_col=args.mfa_col,
    )
    print(json.dumps(result, indent=2))

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Latency summary written to: {args.out_json}")


if __name__ == "__main__":
    main()
