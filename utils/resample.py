#!/usr/bin/env python3
# Oct. 17, 2023.
# Simplified multi-process version, Nov. 2025.

"""
Data pre-processing: recursively resample WAVs to target sample rate using multiple processes.
Input:  INPUT_DIR/**/*.wav
Output: OUTPUT_DIR/<relative_path>.wav (preserves directory structure)
"""

import os
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import soundfile as sf
import librosa
from tqdm import tqdm


def parse_args():
    p = argparse.ArgumentParser(description="Resample WAVs in parallel.")
    p.add_argument("--input_dir", required=True,
                   help="Input directory containing WAV files.")
    p.add_argument("--output_dir", required=True,
                   help="Output directory for resampled WAV files.")
    p.add_argument("--sr", type=int, default=16000,
                   help="Target sample rate.")
    p.add_argument("--workers", type=int, default=32,
                   help="Number of processes.")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip if target file already exists.")
    return p.parse_args()


def target_path_for(src_path: Path, input_dir: Path, output_dir: Path) -> Path:
    """
    Map any source path to: OUTPUT_DIR/<relative_path>.wav
    Preserves the directory structure relative to input_dir.
    """
    try:
        relative_path = src_path.relative_to(input_dir)
        return output_dir / relative_path
    except ValueError:
        # If src_path is not under input_dir, fall back to basename
        return output_dir / src_path.name


def process_one(src: Path, input_dir: Path, output_dir: Path, tgt_sr: int, skip_existing: bool) -> tuple[str, str]:
    """
    Process a single WAV.
    Returns (status, message_or_path), where status in {"ok", "skip", "miss", "fail"}.
    """
    try:
        if not src.exists():
            return ("miss", f"not_found:{src}")

        dst = target_path_for(src, input_dir, output_dir)

        if skip_existing and dst.exists():
            return ("skip", str(dst))

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Read audio
        data, sr = sf.read(src, always_2d=False)

        # Mono
        if hasattr(data, "ndim") and data.ndim > 1:
            data = data.mean(axis=1)

        # Resample if needed (librosa)
        if sr != tgt_sr:
            try:
                data = librosa.resample(y=data, orig_sr=sr, target_sr=tgt_sr)
            except Exception as e:
                return ("fail", f"resample_error:{src}:{e}")

        # Write
        sf.write(dst, data, tgt_sr)
        return ("ok", str(dst))

    except Exception as e:
        return ("fail", f"{src}:{e}")


def collect_wavs(input_dir: Path):
    """
    Recursively collect all .wav under input_dir.
    """
    return list(input_dir.rglob("*.wav"))  # list so we can take len() and iterate multiple times


def main():
    # Avoid over-threading inside each process
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")

    wavs = collect_wavs(input_dir)
    total = len(wavs)
    if total == 0:
        print("No WAV files found. Nothing to do.")
        return

    ok = skip = miss = fail = 0
    errors = []

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = [
            ex.submit(process_one, src, input_dir, output_dir, args.sr, args.skip_existing)
            for src in wavs
        ]
        for fut in tqdm(as_completed(futures), total=total, desc="Resampling", unit="file"):
            status, msg = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            elif status == "miss":
                miss += 1
                errors.append(msg)
            else:
                fail += 1
                errors.append(msg)

    print("\n— Summary —")
    print(f"ok   : {ok}")
    print(f"skip : {skip}")
    print(f"miss : {miss}")
    print(f"fail : {fail}")

    if errors:
        errlog = output_dir / "_errors.log"
        errlog.parent.mkdir(parents=True, exist_ok=True)
        errlog.write_text("\n".join(errors), encoding="utf-8")
        print(f"Errors logged to: {errlog}")


if __name__ == "__main__":
    main()