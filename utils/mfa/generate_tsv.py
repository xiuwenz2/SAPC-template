#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, July 28, 2024.

"""
Data pre-processing: generate .tsv and .origin.wrd manifest.
"""

import argparse, os, re, json
from pydub import AudioSegment
import soundfile as sf
from tqdm import tqdm


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--data-dir", default="./", type=str, metavar="DATA-DIR", help="data dir"
    )
    parser.add_argument(
        "--manifest-dir", default="./aligned/manifest", type=str, metavar="DATA-DIR", help="data dir"
    )
    return parser
            
def main(args):        
    with open(
        os.path.join(args.manifest_dir, args.split + ".tsv"), "w"
    ) as ftsv:
        print("{}".format(os.path.join(args.manifest_dir, args.split)), file=ftsv)
        for root, _, files in os.walk(os.path.join(args.data_dir, "aligned", args.split)):
            for file in tqdm(files):
                fname = os.path.join(root, file)
                tsv = "{}\t{}".format(fname, sf.info(fname).frames)
                print(tsv.strip(), file=ftsv)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
