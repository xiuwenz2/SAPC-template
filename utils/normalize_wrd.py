#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, June 23, 2024.

"""
Data pre-processing: text normalization, .origin.wrd to .wrd.
"""

import argparse, os, re, json
from tqdm import tqdm
from nemo_text_processing.text_normalization.normalize import Normalizer
# PUNC = r"[─()<>\-/\[\]{}｢｣､〜〰–—‛“”„‟…‧﹏.,:?~!\"\+*~;]"

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="name of split"
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
    parser.add_argument(
        '--remove-parentheses', action='store_true', help="removing disfluent parts within paratheses in the transcripts"
    )
    return parser

def main(args):
    
    normalizer = Normalizer(input_case='cased', lang='en')             
    error_correction_dict = json.load(open(os.path.join(args.data_dir, "doc", "SpeechAccessibility_"+args.release+"_Error_Correction.json")))
    abbreviation_decomposition_dict = json.load(open(os.path.join(args.data_dir, "doc", "SpeechAccessibility_"+args.release+"_Abbreviation_Decomposition.json")))

    if args.remove_parentheses:
        out_ext = ".wrd.without.parentheses"
    else:
        out_ext = ".wrd.with.parentheses"
    
    with open(
        os.path.join(args.manifest_dir, args.split + ".tsv"), "r"
    ) as ftsv, open(
        os.path.join(args.manifest_dir, args.split + ".origin.wrd"), "r"
    ) as fin, open(
        os.path.join(args.manifest_dir, args.split + out_ext), "w"
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
            trans = error_correction_dict[fname].strip() if fname in error_correction_dict else trans
            trans = abbreviation_decomposition_dict[fname].strip() if fname in abbreviation_decomposition_dict else trans
            ### including mismatch caused by the normalizer, mismatch of the brackets, utt with abnormal WER, abbr issues...
            
            if args.remove_parentheses:
                # process "(...)" by removing them while keeping "(cs:...)"
                content = re.findall("\((.*?)\)", trans)
                if len(content) > 0:
                    content_ = [re.sub("(.+(?=:))", " ", con) if re.findall("(.+(?=:))", con) else "" for con in content]
                    mapping = {content[i]:re.sub(":", " ", content_[i]) for i in range(len(content))}
                    trans = re.sub("\((.*?)\)", lambda x: mapping[x.group()[1:-1]], trans)
            else:
                assert args.remove_parentheses is False
                trans = re.sub("\((.*?)\)", lambda x: "("+re.sub("(.+(?=:))", " ", x.group()[1:-1])+")", trans) ### this rule keeps "(...)" rather than removing them
            
            # upper case
            trans = trans.upper()
            
            # remove punc except "\'"
            codes = '''
            \u0041-\u005a\u0027\u0020
            \u00c0\u00c1\u00c4\u00c5\u00c8\u00c9\u00cd\u00cf
            \u00d1\u00d3\u00d6\u00d8\u00db\u00dc
            \u0106
            ''' 
            trans = re.sub(u"([^"+codes+"])", " ", trans)

            # remove extra "'"
            trans = " ".join([con.strip("'") for con in trans.split()])

            # remove extra space
            s = ' '.join(trans.strip().split())
            
            fout.write(f'{s}\n')
    
if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
