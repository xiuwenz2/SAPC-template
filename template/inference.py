#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, July 10, 2024.

"""
SAPC inference file with whisper base model. Please modify it w.r.t. your own model.
"""

import argparse, os
from tqdm import tqdm
import whisper

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-pth", default="/taiga/data/processed", type=str, metavar="DATA_PTH", help="data_pth"
    )
    parser.add_argument(
        "--manifest-pth", default="/taiga/manifest", type=str, metavar="MANIFEST_PTH", help="manifest_pth"
    )
    parser.add_argument(
        "--split", default="test1", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--output-name", default="/taiga/downloads/???/???/inference/???.hypo", type=str, metavar="OUTPUT-NAME", help="???s represent team name, submission pk, and split."
    )
    return parser

def main(args):
    
    ######## TO-DO 1: load your own model ########
    model = whisper.load_model("base")
    tokenizer = whisper.tokenizer.get_tokenizer(multilingual=False)
    number_tokens = [
        i
        for i in range(tokenizer.eot)
        if all(c in "0123456789$%&-–—+£=�*…•" for c in tokenizer.decode([i]).removeprefix(" "))
    ]
    ##############################################
    
    ### Dump Inference Results
    manifest = os.path.join(args.manifest_pth, args.split + ".tsv")
    with open(manifest, "r") as ftsv, open(args.output_name, "w") as fhypo:
        next(ftsv)
        for t in tqdm(ftsv.readlines()):
            fname = t.strip().split()[0].split("/")[-1]
            
            ######## TO-DO 2: modify the following inference scripts ########
            result = model.transcribe(
                os.path.join(args.data_pth, args.split, fname),
                suppress_tokens=[-1] + number_tokens,
                temperature=0.0
            )
            #################################################################
            
            print(result["text"].strip(), file=fhypo)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
