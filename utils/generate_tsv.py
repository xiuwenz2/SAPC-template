#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, Oct.17, 2023.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Data pre-processing: generate .tsv manifest.
"""

import argparse, os
import soundfile as sf


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag", default="dev", type=str, metavar="TAG", help="name of split"
    )
    parser.add_argument(
        "--datadest", default="/home/xiuwenz2/SpeechAcc/data/2023-10-05", type=str, metavar="DATADEST", help="dest directory containing new wav files to index"
    )
    parser.add_argument(
        "--manifest-dir", default="/home/xiuwenz2/SpeechAcc/level-class/manifest/2023-10-05", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def main(args):
    with open(os.path.join(args.manifest_dir, args.tag + ".tsv"), "w") as fout:
        print("{}".format(os.path.join(args.manifest_dir, args.tag)), file=fout)
        for root, _, files in os.walk(os.path.join(args.datadest, args.tag)):
            for file in files:
                fname = os.path.join(args.datadest, args.tag, file)
                frames = sf.info(fname).frames
                print("{}\t{}".format(fname, frames), file=fout)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
