#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, June 23, 2024.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Data pre-processing: text normalization, .origin.wrd to .wrd.
"""

import argparse, os, re
from tqdm import tqdm
from nemo_text_processing.text_normalization.normalize import Normalizer
PUNC = r"[。─()-<>！？｡\"＂＃＄％＆＇（）＊＋，－-／/：；＜＝＞＠［＼］＾＿｀｛｜｝\[\]{～}｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏.,:?~!]"

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="name of split"
    )
    parser.add_argument(
        "--manifest-dir", default="/home/xiuwenz2/SpeechAcc/fine-tune/manifest/2023-10-05", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def main(args):
    normalizer = Normalizer(input_case='cased', lang='en')
    with open(
        os.path.join(args.manifest_dir, args.split+".origin.wrd"), "r"
    ) as fin, open(
        os.path.join(args.manifest_dir, args.split+".wrd"), "w"
    ) as fout:
        for item in tqdm(fin.readlines()):
            trans = item.strip()
            
            # change "\’" & "\‘" back to "\'"
            trans = re.sub(r"[\’\‘]", r"[\']", trans)
            
            # remove "*", "~" before nemo_text_processing
            trans = re.sub(r"[\*\~]", " ", trans)
            
            # nemo_text_processing
            trans = normalizer.normalize(trans, verbose=False, punct_post_process=True)
            
            # normalize unusual email addresses
            content = re.findall("@", trans)
            if len(content) > 0:
                content = [re.sub("\.", " dot ", con[:-1])+con[-1] for con in trans.split()]
                trans = " ".join(content)
                trans = re.sub("@", " at ", trans)
            
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
                content_ = ["UNK" if ((re.findall("(.+(?=:))", con) and (re.findall("(.+(?=:))", con)[0]=="w" or re.findall("(.+(?=:))", con)[0]=="u")) or con==" ") else re.sub("(.+(?=:))", " ", con) for con in content]
                mapping = {content[i]:re.sub(":", " ", content_[i]) for i in range(len(content))}
                trans = re.sub("\{(.*?)\}", lambda x: "{"+mapping[x.group()[1:-1]]+"}", trans)
            
            ### the manual replacement part fill in here...
            ### including mismatch caused by the normalizer, mismatch of the brackets, utt with abnormal WER...
            
            # process "(...)" by removing them
            content = re.findall("\((.*?)\)", trans)
            if len(content) > 0:
                trans = re.sub("\((.*?)\)", " ", trans)
#                 trans = re.sub("\((.*?)\)", lambda x: "("+re.sub("(.+(?=:))", " ", x.group()[1:-1])+")", trans) ### this rule keeps "(...)" rather than removing them
            
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
