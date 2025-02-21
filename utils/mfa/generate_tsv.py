#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, July 28, 2024.

import argparse
import os
import soundfile as sf
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--data-dir", default="./", type=str, metavar="DATA-DIR", help="data dir"
    )
    parser.add_argument(
        "--manifest-dir", default="./aligned/manifest", type=str, metavar="MANIFEST-DIR", help="manifest dir"
    )
    return parser

def process_file(fname):
    try:
        frames = sf.info(fname).frames
        return f"{fname}\t{frames}"
    except Exception as e:
        return None

def main(args):
    out_tsv = os.path.join(args.manifest_dir, f"{args.split}.tsv")
    os.makedirs(args.manifest_dir, exist_ok=True)
    
    file_list = []
    base_path = os.path.join(args.data_dir, "aligned", args.split)
    for root, _, files in os.walk(base_path):
        for file in files:
            fname = os.path.join(root, file)
            file_list.append(fname)
    
    with open(out_tsv, "w") as ftsv:
        print(os.path.join(args.manifest_dir, args.split), file=ftsv)
        
        with Pool(cpu_count()) as pool:
            for result in tqdm(pool.imap_unordered(process_file, file_list), total=len(file_list)):
                if result is not None:
                    print(result, file=ftsv)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
