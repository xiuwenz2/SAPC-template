import argparse, os, re, torch, json
from metrics import calculate_word_error_rate, SemScore
from tqdm import tqdm


def process_punc(trans):

    codes = '''
            \u0041-\u005a\u0027\u0020
            \u00c0\u00c1\u00c4\u00c5\u00c8\u00c9\u00cd\u00cf
            \u00d1\u00d3\u00d6\u00d8\u00db\u00dc\u0106
            '''

    trans = trans.strip().upper()
    trans = re.sub(u"([^"+codes+"])", "", trans)
    trans = ' '.join(trans.strip().split())

    return trans

def evaluate(submission, hypo_pth, ref_pth, **kwargs):
    print("Starting Evaluation.....")
    
    output = {"test_1_split":[], "test_2_split":[]}

    for split, split_name in zip(["test1", "test2"], ["test_1_split", "test_2_split"]):
        
        ### Loading transcripts
        references = {"ref1":[], "ref2":[]}
        hypotheses = []

        with open(
            os.path.join(ref_pth, split+".ref1"), "r"
            ) as fref1, open(
            os.path.join(ref_pth, split+".ref2"), "r"
            ) as fref2, open(
            os.path.join(hypo_pth, split+".hypo"), "r"
            ) as fhypo:
            for r1, r2, h in tqdm(zip(fref1.readlines(), fref2.readlines(), fhypo.readlines())):
                references['ref1'].append(process_punc(r1.strip()))
                references['ref2'].append(process_punc(r2.strip()))
                hypotheses.append(process_punc(h.strip()))

        ### Calculating WER
        wer = calculate_word_error_rate(references["ref1"], references["ref2"], hypotheses)
        
        ### Calculating SemScore
        semscores = {}
        for ref_type in ["ref1", "ref2"]:
            semscores[ref_type] = SemScore().score_all(refs=references[ref_type], hyps=hypotheses)
        semscore = [i if i > j else j for i, j in zip(semscores["ref1"], semscores["ref2"])]

        output[split_name] = [round(wer * 100, 4), round(sum(semscore) / len(semscore) * 100, 4)]

    json.dump(output, open(os.path.join("/taiga", "results", submission+".json"), "w"), indent=6)
    print(f"The evaluation for submission {submission} has been successfully completed.")
    
    return output

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--submission-team-name", default="???", metavar="SUBMISSION-TEAM-NAME", help="submission team name"
    )
    parser.add_argument(
        "--submission-pk", default="???", metavar="SUBMISSION-PK", help="submission pk"
    )
    return parser

if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()

    evaluate(args.submission_pk, os.path.join("/taiga/downloads", args.submission_team_name, args.submission_pk, "inference"), "/taiga/manifest")
