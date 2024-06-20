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
        "--split", default="dev", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--data-dir", default="???", type=str, metavar="DATA-DIR", help="data dir containing processed wav files to index"
    )
    parser.add_argument(
        "--manifest-dir", default="???", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def main(args):
    with open(os.path.join(args.manifest_dir, args.split + ".tsv"), "w") as fout:
        print("{}".format(os.path.join(args.manifest_dir, args.split)), file=fout)
        for root, _, files in os.walk(os.path.join(args.data_dir, args.split)):
            for file in files:
                fname = os.path.join(args.data_dir, args.split, file)
                frames = sf.info(fname).frames
                print("{}\t{}".format(fname, frames), file=fout)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
