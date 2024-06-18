#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, Oct.17, 2023.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Data pre-processing: Nemo text normalization, .origin.wrd to .wrd.
"""

import argparse, os, re, joblib
from tqdm import tqdm
from nemo_text_processing.text_normalization.normalize import Normalizer
PUNC = r"[。─()-<>！？｡\"＂＃＄％＆＇（）＊＋，－-／/：；＜＝＞＠［＼］＾＿｀｛｜｝\[\]{～}｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏.,:?~!]"

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag", default="dev", type=str, metavar="TAG", help="name of split"
    )
    parser.add_argument(
        "--datadest", default="/home/xiuwenz2/SpeechAcc/data/2023-10-05", type=str, metavar="DATADEST", help="dest directory containing new wav files to index"
    )
    parser.add_argument(
        "--manifest-dir", default="/home/xiuwenz2/SpeechAcc/fine-tune/manifest/2023-10-05", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def generate_content(content, doc_pt, ):
    for root, ds, fs in os.walk(doc_pt):
        for f in fs:
            assert f.endswith(".json")
            with open(os.path.join(root, f), "r") as fin:
                for item in json.load(fin)['Files']:
                    fname = item['Filename']
                    content[fname] = item["Prompt"]["Transcript"]
    return content

def main(args):
    content = generate_content({}, os.path.join(args.datadest, "doc"), )
    with open(
        os.path.join(args.manifest_dir, args.tag+".tsv"), "r"
    ) as tsv_data, open(
        os.path.join(args.manifest_dir, args.tag+".origin.wrd"), "w"
    ) as wrd_data, open(
        os.path.join(args.manifest_dir, args.tag+".origin.wrd.exp"), "w"
    ) as wrd_exp:
        next(tsv_data)
        for i, line in tqdm(enumerate(tsv_data.readlines())):
            fname = line.split()[0].split("/")[-1]
#             fid = fname.split("_")[0].upper()
#             prompt = content[fid][fname]['Prompt']
            trans = content[fname]
            try:
#                 trans = re.sub(u"\n", " ", trans)
                assert len(trans.split("\n"))==1
            except:
#                 print([fname, trans.split("\n")], file=wrd_exp)
#                 trans = "EXP"
                trans = re.sub(u"\n", " ", trans)
#                 if "#ts" in trans:
#                     print((i, fname, trans), file=wrd_exp)
            print(trans, file=wrd_data)
#     space_char = '|'
#     normalizer = Normalizer(input_case='cased', lang='en')
#     with open(os.path.join(args.manifest_dir, args.tag+".origin.wrd"), "r") as fin, open(os.path.join(args.manifest_dir, args.tag+".wrd"), "w") as fout:
#         for item in fin:
#             trans = item.strip()
            
#             # remove "[...]"
#             ### trans = re.sub(u"\\[.*?] ", "", trans)
#             trans = re.sub("\[(.*?)\]", " ", trans)
            
#             # process "{...}"
#             content = re.findall("\{(.*?)\}", trans)
#             if len(content) > 0:
#                 content_ = ["UNK" if ((re.findall("(.+(?=:))", con) and (re.findall("(.+(?=:))", con)[0]=="w" or re.findall("(.+(?=:))", con)[0]=="u")) or con==" ") else re.sub("(.+(?=:))", " ", con) for con in content]
#                 mapping = {content[i]:re.sub(":", " ", content_[i]) for i in range(len(content))}
#                 trans = re.sub("\{(.*?)\}", lambda x: "{"+mapping[x.group()[1:-1]]+"}", trans)
            
#             # process "(...)"
#             content = re.findall("\((.*?)\)", trans)
#             if len(content) > 0:
#                 trans = re.sub("\((.*?)\)", lambda x: "("+re.sub("(.+(?=:))", " ", x.group()[1:-1])+")", trans)
                
#             # process "...]"
#             content = re.findall("(.*?)\]", trans)
#             if len(content) > 0:
#                 trans = re.sub("(.*?)\]", " ", trans)
            
#             # normalize "\’" & "\‘" to "\'"
#             trans = re.sub(r"[\’\‘]", r"[\']", trans)
            
#             # remove "*", "~" before nemo_text_processing
#             trans = re.sub(r"[\*\~]", " ", trans)
            
#             # nemo_text_processing
#             trans = normalizer.normalize(trans, verbose=False, punct_post_process=True)
            
#             # normalize unusual email addresses
#             content = re.findall("@", trans)
#             if len(content) > 0:
#                 content = [re.sub("\.", " dot ", con[:-1])+con[-1] for con in trans.split()]
#                 trans = " ".join(content)
#                 trans = re.sub("@", " at ", trans)
            
#             # remove punc
#             trans = re.sub(PUNC, " ", trans)
            
#             # remove extra "'"
#             trans = " ".join([con.strip("'") for con in trans.split()])
            
#             # upper case
#             trans = trans.upper()
            
#             # remove extra space
#             s = ' '.join(trans.strip().split())
# #             s = ' '.join(s.replace(' ', space_char))
#             fout.write(f'{s}\n')
    
if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
