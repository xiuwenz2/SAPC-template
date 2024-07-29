#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, June 23, 2024.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Data pre-processing: text normalization, .origin.wrd to .wrd.
"""

import argparse, os, re, json
from tqdm import tqdm
from nemo_text_processing.text_normalization.normalize import Normalizer
PUNC = r"[─()<>\-/\[\]{}｢｣､〜〰–—‛“”„‟…‧﹏.,:?~!\"\+*~]"

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="name of split"
    )
    parser.add_argument(
        "--release", default="???", type=str, metavar="DATADEST", help="release of the dataset"
    )
    parser.add_argument(
        "--doc-dir", default="???", type=str, metavar="DATA-DIR", help="dir containing doc files"
    )
    parser.add_argument(
        "--manifest-dir", default="???", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    parser.add_argument(
        '--with-parentheses', action='store_true', metavar="WITH-PARENTHESES", help="keeping disfluent parts within paratheses in the transcripts"
    )
    return parser

def main(args):
    
    normalizer = Normalizer(input_case='cased', lang='en')                   
    
    dict_error_correction = json.load(open(os.path.join(args.doc_dir, "SpeechAccessibility_"+args.release+"_"+"Error_Correction.json")))
    dict_abbreviation_decomposition = json.load(open(os.path.join(args.doc_dir, "SpeechAccessibility_"+args.release+"_"+"Abbreviation_Decomposition.json")))
    
    with open(
        os.path.join(args.manifest_dir, args.split + ".tsv"), "r"
    ) as ftsv, open(
        os.path.join(args.manifest_dir, args.split+".origin.wrd"), "r"
    ) as fin, open(
        os.path.join(args.manifest_dir, args.split+".postnorm.wrd"), "w"
    ) as fout:
        next(ftsv)
        for item, t in tqdm(zip(fin.readlines(), ftsv.readlines())):            
            
            trans = item.strip()
            
            # change "\’" & "\‘" back to "\'"
            trans = re.sub(r"[\’\‘]", r"'", trans)
            
            # remove "[...]" by removing them
            ### trans = re.sub(u"\\[.*?] ", "", trans)
            trans = re.sub("\[(.*?)\]", " ", trans)
            
            # process "...]"
            content = re.findall("(.*?)\]", trans)
            if len(content) > 0:
                trans = re.sub("(.*?)\]", " ", trans)
            
            # process "{...}" by replacing unknown words and retaining uncertain words
            content = re.findall("\{(.*?)\}", trans)
            if len(content) > 0:
                content_ = []
                for con in content:
                    if re.findall("(.+(?=:))", con) and re.findall("(.+(?=:))", con)[0]=="w":
                        assert len(re.findall(r"\d+", con)) == 1
                        num_unk = int(re.findall(r"\d+", con)[0])
                        content_.append(" ".join(["UNK" for i in range(num_unk)]))
                    elif (re.findall("(.+(?=:))", con) and re.findall("(.+(?=:))", con)[0]=="u") or con==" ":
                        content_.append(" ".join(["UNK" for i in range(1)]))
                    else:
                        content_.append(re.sub("(.+(?=:))", " ", con))
                mapping = {content[i]:re.sub(":", " ", content_[i]) for i in range(len(content))}
                trans = re.sub("\{(.*?)\}", lambda x: "{"+mapping[x.group()[1:-1]]+"}", trans)
                
            # remove "*", "~" before nemo_text_processing
            trans = re.sub(r"[\*\~]", " ", trans)
            
            # nemo_text_processing
            trans = ' '.join(trans.strip().split()) ### remove extra space
            trans = normalizer.normalize(trans, verbose=False, punct_post_process=True)
            
            # normalize unusual email addresses
            content = re.findall("@", trans)
            if len(content) > 0:
                content = [re.sub("\.", " dot ", con[:-1])+con[-1] for con in trans.split()]
                trans = " ".join(content)
                trans = re.sub("@", " at ", trans)
            
            # fix trans mismatch manually
            ### including mismatch caused by the normalizer, mismatch of brackets, utt with abnormal WER, M.P. issue...
            fname = t.strip().split()[0].split("/")[-1]
            trans = dict_error_correction[fname].strip() if fname in dict_error_correction else trans
            trans = dict_abbreviation_decomposition[fname].strip() if fname in dict_abbreviation_decomposition else trans
            ### including mismatch caused by the normalizer, mismatch of the brackets, utt with abnormal WER, abbr issues...
            
            if not args.with_parentheses:
                # process "(...)" by removing them while keeping "(cs:...)"
                content = re.findall("\((.*?)\)", trans)
                if len(content) > 0:
                    content_ = [re.sub("(.+(?=:))", " ", con) if re.findall("(.+(?=:))", con) else "" for con in content]
                    mapping = {content[i]:re.sub(":", " ", content_[i]) for i in range(len(content))}
                    trans = re.sub("\((.*?)\)", lambda x: mapping[x.group()[1:-1]], trans)
            else:
                assert args.with_parentheses is True
                trans = re.sub("\((.*?)\)", lambda x: "("+re.sub("(.+(?=:))", " ", x.group()[1:-1])+")", trans) ### this rule keeps "(...)" rather than removing them
            
            # remove punc except "\'"
            trans = re.sub(PUNC, " ", trans)
            
            # remove extra "'"
            trans = " ".join([con.strip("'") for con in trans.split()])
            
            # upper case
            trans = trans.upper()
            
            # remove extra space
            s = ' '.join(trans.strip().split())
            
            fout.write(f'{s}\n')
    
if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
