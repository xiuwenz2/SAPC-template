#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, Oct. 17, 2023.

"""
Data pre-processing: resample audios to 16k.
"""

import argparse, os, json, librosa
import soundfile as sf


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--release", default="???", type=str, metavar="DATADEST", help="release of the dataset"
    )
    parser.add_argument(
        "--database", default="???", metavar="DATABASE", help="data dir"
    )
    parser.add_argument(
        "--sr", default=16000, type=int, metavar="SAMPLERATE", help="ideal sample rate"
    )
    return parser

def get_fn(database, release, split):
    with open(
        os.path.join(database, "doc", "SpeechAccessibility_"+release+"_Split_by_Contributors.json"), 'r'
    ) as f:
        for contributor in json.load(f)[split]:
            for _, _, files in os.walk(os.path.join(database, "raw", contributor)):
                for file in files:
                    if not file.endswith(".wav"):
                        continue
                    yield os.path.join(database, "raw", contributor, file)

def main(args):
    for fname in get_fn(args.database, args.release, args.split):
        targ_path = os.path.join(args.database, "processed", args.split, fname.split("/")[-1])
        if os.path.exists(targ_path):
            continue
        data, sr = sf.read(fname)
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        if sr != args.sr:
            try:
                data = librosa.resample(data, orig_sr=sr, target_sr=args.sr)
            except:
                print("Skip", fname, ", as it is not in the right format.")
                continue
        sf.write(targ_path, data, args.sr)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
