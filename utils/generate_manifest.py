#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, Oct.17, 2023.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
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
        "--data-dir", default="???", type=str, metavar="DATA-DIR", help="data dir containing processed wav files to index"
    )
    parser.add_argument(
        "--manifest-dir", default="???", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def generate_content(content, doc_pt, ):
    for root, ds, fs in os.walk(doc_pt):
        for f in fs:
            assert f.endswith(".json")
            with open(os.path.join(root, f), "r") as fin:
                try:
                    for item in json.load(fin)['Files']:
                        fname = item['Filename']
                        content[fname] = item["Prompt"]["Transcript"]
                except:
                    continue
    return content

def process_timesteps(fpt, trans):
    trans = re.sub(u"\\[.*?]", "", trans).strip()
    timestamps = trans.split('\n')[1:]
        
    audio = AudioSegment.from_wav(fpt)
    combined = AudioSegment.empty()
    transcriptions = []
    
    for timestamp in timestamps:
        ts_ls = timestamp.strip().split()
        start_time = float(ts_ls[0].strip()) * 1000  
        end_time = float(ts_ls[1].strip()) * 1000 

        segment = audio[start_time:end_time]
        combined += segment
        transcriptions.append(" ".join(ts_ls[2:]))

    output_file_final_root = fpt.split(".")[0]+"_processed_ts.wav"
    combined.export(output_file_final_root, format="wav")
                
    return " ".join(transcriptions), "{}\t{}".format(output_file_final_root, sf.info(output_file_final_root).frames)
            
def main(args):
    content = generate_content({}, os.path.join(args.data_dir, "../doc"), )
    with open(
        os.path.join(args.manifest_dir, args.split + ".tsv"), "w"
    ) as ftsv, open(
        os.path.join(args.manifest_dir, args.split+".origin.wrd"), "w"
    ) as fwrd:
        print("{}".format(os.path.join(args.manifest_dir, args.split)), file=ftsv)
        for root, _, files in os.walk(os.path.join(args.data_dir, args.split)):
            for file in tqdm(files):
                if file.endswith("_processed_ts.wav"):
                    continue
                fname = os.path.join(args.data_dir, args.split, file)
                trans = content[file]
                if "#ts" in trans:
                    trans, tsv = process_timesteps(fname, trans)
                else:
                    trans = re.sub(u"\n", " ", trans)
                    tsv = "{}\t{}".format(fname, sf.info(fname).frames)
                print(tsv.strip(), file=ftsv)
                print(trans.strip(), file=fwrd)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)