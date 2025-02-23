#!/usr/bin/env python3
# By xiuwenz2@illinois.edu, June 23, 2024.

"""
Data pre-processing: text normalization, .origin.wrd to .wrd.
"""

import argparse, os, re, json
from tqdm import tqdm
from multiprocessing import Pool
# from nemo_text_processing.text_normalization.normalize import Normalizer
# PUNC = r"[─()<>\-/\[\]{}｢｣､〜〰–—‛“”„‟…‧﹏.,:?~!\"\+*~;]"

word_ls = ['MSNNBC', 'MSNBC', 'MSSNNBC', 'AARP', 'ACDC', 'ADHD', 'BBBC', 'ESPN', 'HGTV', 'LBGQ', 'NCIS', 'NPPA', 'PTSD', 'RAMC', 
           'SPCA', 'TLSC', 'WDRB', 'WDTN', 'WHIO', 'WHYY', 'WKRP', 'WNBA', 'WNYC', 'YMCA', 'AAA', 'ABC', 'ACP', 'ADA', 'AHS', 
           'AJR', 'AKA', 'ALS', 'AMC', 'AOL', 'AXL', 'BAU', 'BBC', 'BLT', 'BMW', 'BRB', 'BST', 'BTS', 'CBS', 'CCM',
           'CEO', 'CFO', 'CIA', 'CNC', 'CNN', 'CPR', 'CSI', 'CVS', 'DCI', 'DDA', 'DNA', 'DSW', 'DVD', 'DVR', 'FAC', 
           'FBI', 'FDR', 'GPA', 'HBO', 'ICS', 'IRS', 'JFK', 'LAL', 'LSU', 'MGK', 'MIT', 'MMA', 'MSN', 'NBA', 'NBC', 
           'NCI', 'NFL', 'NHK', 'NHL', 'NPR', 'NRA', 'OAN', 'OCD', 'PBC', 'PBS', 'PDU', 'PGA', 'PLS', 'PSP', 'RBG', 
           'REM', 'REO', 'RSD', 'SNL', 'TBS', 'TNT', 'TSA', 'UPS', 'USA', 'USC', 'VSP', 'WRB', 'AC', 'AD', 'AI', 'AM', 
           'AV', 'BB', 'BJ', 'CD', 'CJ', 'CO', 'CV', 'DC', 'DJ', 'DV', 'ER', 'ES', 'FC', 'FO', 'FX', 'GI', 'GP', 
           'GR', 'GT', 'ID', 'IV', 'JF', 'JJ', 'KC', 'LA', 'MP', 'NP', 'OJ', 'OK', 'PA', 'PC', 'PD', 'PJ', 
           'PM', 'PT', 'QR', 'RC', 'RH', 'RV', 'TV', 'UK', 'US', 'WH', 'WO', 'XM', 'PPM', 'TX', 'NYC', 'TTV',
          'II', 'AAM', 'IL', 'NI', 'SG', 'PB', 'NSYNC', 'YK', 'AJ', 'PBJ']

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

def init_worker(data_dir, release, remove_parentheses):
    global normalizer, REMOVE_PARENTHESES
    from nemo_text_processing.text_normalization.normalize import Normalizer
    normalizer = Normalizer(input_case='cased', lang='en')
    #error_correction_path = os.path.join(data_dir, "doc", "SpeechAccessibility_" + release + "_Error_Correction.json")
    #abbreviation_decomposition_path = os.path.join(data_dir, "doc", "SpeechAccessibility_" + release + "_Abbreviation_Decomposition.json")
    #error_correction_dict = json.load(open(error_correction_path, "r"))
    #abbreviation_decomposition_dict = json.load(open(abbreviation_decomposition_path, "r"))
    REMOVE_PARENTHESES = remove_parentheses

def separate_abbreviation(word):
    return " ".join(word)

def process_line(args):
    origin_line, manifest_line = args
    fname = manifest_line.strip().split()[0].split("/")[-1]
    trans = origin_line.strip()
            
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
                if len(re.findall(r"\d+", con)) == 0:
                    content_.append(" ")
                    continue
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
            # fname = t.strip().split()[0].split("/")[-1]
            # trans = error_correction_dict[fname].strip() if fname in error_correction_dict else trans
            # trans = abbreviation_decomposition_dict[fname].strip() if fname in abbreviation_decomposition_dict else trans
            ### including mismatch caused by the normalizer, mismatch of the brackets, utt with abnormal WER, abbr issues...
            
    if REMOVE_PARENTHESES:
        # process "(...)" by removing them while keeping "(cs:...)"
        content = re.findall("\((.*?)\)", trans)
        if len(content) > 0:
            content_ = [re.sub("(.+(?=:))", " ", con) if re.findall("(.+(?=:))", con) else "" for con in content]
            mapping = {content[i]:re.sub(":", " ", content_[i]) for i in range(len(content))}
            trans = re.sub("\((.*?)\)", lambda x: mapping[x.group()[1:-1]], trans)
    else:
        assert REMOVE_PARENTHESES is False
        trans = re.sub("\((.*?)\)", lambda x: "("+re.sub("(.+(?=:))", " ", x.group()[1:-1])+")", trans) ### this rule keeps "(...)" rather than removing them
    
    # separate abbreviation
    words = trans.strip().split()
    new_words = []
    for word in words:
        if word in word_ls:
            new_words.append(separate_abbreviation(word))
        else:
            new_words.append(word)
    trans = ' '.join(new_words)
           
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
    trans = ' '.join(trans.strip().split())
            
    #fout.write(f'{s}\n')
    return trans

def main(args):
    manifest_path = os.path.join(args.manifest_dir, args.split + ".tsv")
    origin_path = os.path.join(args.manifest_dir, args.split + ".origin.wrd")
    out_ext = ".wrd.without.parentheses" if args.remove_parentheses else ".wrd.with.parentheses"
    output_path = os.path.join(args.manifest_dir, args.split + out_ext)

    with open(origin_path, "r") as fin:
        origin_lines = fin.readlines()
    with open(manifest_path, "r") as ftsv:
        manifest_lines = ftsv.readlines()
    
    if manifest_lines:
        header = manifest_lines.pop(0)
    
    args_list = list(zip(origin_lines, manifest_lines))
    
    '''
    if args.remove_parentheses:
        out_ext = ".wrd.without.parentheses"
    else:
        out_ext = ".wrd.with.parentheses"
    '''
    
    with Pool(initializer=init_worker, initargs=(args.data_dir, args.release, args.remove_parentheses)) as pool:
        results = list(tqdm(pool.imap(process_line, args_list), total=len(args_list)))

    with open(output_path, "w") as fout:
        for line in results:
            fout.write(line + "\n")
    
if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
