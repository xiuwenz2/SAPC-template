import os, argparse

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="name of split"
    )
    parser.add_argument(
        "--data-dir", default="./processed", type=str, metavar="DATA-DIR", help="data dir"
    )
    parser.add_argument(
        "--manifest-dir", default="./manifest", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def main(args):
    
    content = {}
    manifest_path = os.path.join(args.manifest_dir, args.split + ".tsv")
    origin_path = os.path.join(args.manifest_dir, args.split + ".wrd.with.parentheses")
    with open(origin_path, "r") as fin, open(manifest_path, "r") as ftsv:
        next(ftsv)
        for w, t in zip(fin.readlines(), ftsv.readlines()):
            content[t.strip().split()[0].split("/")[-1]] = w.strip()

    for root, _, files in os.walk('./data/segmented/dev/'):
         for f in files:
              with open(f"./data/segmented/dev/{f[:-4]}.lab", "w") as fout:
                print(content[f].strip(), file=fout)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)