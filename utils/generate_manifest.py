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
        "--release", default="???", type=str, metavar="DATADEST", help="release of the dataset"
    )
    parser.add_argument(
        "--data-dir", default="???", type=str, metavar="DATA-DIR", help="data dir"
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

def process_timestamps(fpt, trans):
    trans = re.sub(u"\\[.*?]", "", trans).strip()
    timestamps = trans.strip().split('\n')[1:]
    
    duration = 0
    transcriptions = []
    
    for timestamp in timestamps:
        if timestamp.strip() in ["", "#ts"]:
            continue
        ts_ls = timestamp.strip().split()
        duration += (float(ts_ls[1].strip().strip(".")) - float(ts_ls[0].strip().strip(".")))
        transcriptions.append(" ".join(ts_ls[2:]))
    
    if abs(round(duration, 2) - round(sf.info(fpt).duration, 2)) <= 0.02:
        # print("Timestamps are already processed for", fpt)
        return " ".join(transcriptions), "{}\t{}".format(fpt, sf.info(fpt).frames)
        
    audio = AudioSegment.from_wav(fpt)
    combined = AudioSegment.empty() 
    
    for timestamp in timestamps:
        if timestamp.strip() in ["", "#ts"]:
            continue
        ts_ls = timestamp.strip().split()
        start_time = float(ts_ls[0].strip().strip(".")) * 1000
        end_time = float(ts_ls[1].strip().strip(".")) * 1000
        
        combined += audio[start_time:end_time]
    
    combined.export(fpt, format="wav")
    
    return " ".join(transcriptions), "{}\t{}".format(fpt, sf.info(fpt).frames)
            
def main(args):
    content = generate_content({}, os.path.join(args.data_dir, "doc"), )
    
    audio_excluded_dict = json.load(open(os.path.join(args.data_dir, "doc", "SpeechAccessibility_"+args.release+"_Audio_Excluded.json")))
    
    with open(
        os.path.join(args.manifest_dir, args.split + ".tsv"), "w"
    ) as ftsv, open(
        os.path.join(args.manifest_dir, args.split+".origin.wrd"), "w"
    ) as fwrd:
        print("{}".format(os.path.join(args.manifest_dir, args.split)), file=ftsv)
        for root, _, files in os.walk(os.path.join(args.data_dir, "processed", args.split)):
            for file in tqdm(files):
                fname = os.path.join(args.data_dir, "processed", args.split, file)
                if file in audio_excluded_dict:
                    print("Skip", file, ", as it is excluded in the new release.")
                    continue
                try:
                    trans = content[file]
                except:
                    print("Skip", file, ", as it is not found in the new release.")
                    continue
                if "#ts" in trans:
                    trans, tsv = process_timestamps(fname, trans)
                else:
                    trans = re.sub(u"\n", " ", trans)
                    tsv = "{}\t{}".format(fname, sf.info(fname).frames)
                print(tsv.strip(), file=ftsv)
                print(trans.strip(), file=fwrd)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
