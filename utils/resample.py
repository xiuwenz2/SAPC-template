#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, Oct.17, 2023.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Data pre-processing: resample audios to 16k.
"""

import argparse, os, json, librosa
import soundfile as sf


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag", default="dev", type=str, metavar="TAG", help="name of split"
    )
    parser.add_argument(
        "--database", default="/home/xiuwenz2/datasets/SpeechAcc/2023-10-05", metavar="DATABASE", help="root directory containing wav files to index"
    )
    parser.add_argument(
        "--datadest", default="/home/xiuwenz2/SpeechAcc/data/2023-10-05", type=str, metavar="DATADEST", help="dest directory containing new wav files to index"
    )
    parser.add_argument(
        "--sr", default=16000, type=int, metavar="SAMPLERATE", help="ideal sample rate"
    )
    return parser

def get_fn(database, release, tag, ext):
    with open(
        os.path.join(database, "SpeechAccessibility_"+release+"_Split_by_Contributors.json"), 'r'
    ) as f:
        for contributor in json.load(f)[tag]:
            for _, _, files in os.walk(os.path.join(database, contributor)):
                for file in files:
                    if not file.endswith(ext):
                        continue
                    yield os.path.join(database, contributor, file)

def main(args):
    for fname in get_fn(args.database, args.release, args.tag, args.ext):
        targ_path = os.path.join(args.datadest, args.tag, fname.split("/")[-1])
        if os.path.exists(targ_path):
            continue
        data, sr = sf.read(fname)
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        if sr != args.sr:
            try:
                data = librosa.resample(data, orig_sr=sr, target_sr=args.sr)
            except:
                print("Skipping", fname)
                continue
        sf.write(targ_path, data, args.sr)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
