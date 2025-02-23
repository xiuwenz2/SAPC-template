import random, argparse, os
random.seed(42) 

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="name of split"
    )
    parser.add_argument(
        "--data-dir", default="./", type=str, metavar="DATA-DIR", help="data dir"
    )
    parser.add_argument(
        "--manifest-dir", default="../manifest/origin", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    parser.add_argument(
        "--aligned-manifest-dir", default="./aligned/manifest", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    parser.add_argument(
        "--output-manifest-dir", default="../manifest/aligned", metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    parser.add_argument(
        "--sr", default="???", type=int, metavar="MANIFEST-DIR", help="manifest directory containing .tsv files"
    )
    return parser

def load_manifest(tsv_path, wrd_parent_path, wrd_without_path):
    with open(tsv_path, 'r', encoding='utf-8') as f_tsv, \
         open(wrd_parent_path, 'r', encoding='utf-8') as f_parent, \
         open(wrd_without_path, 'r', encoding='utf-8') as f_without:
        next(f_tsv)
        tsv_lines = f_tsv.readlines()
        parent_lines = f_parent.readlines()
        without_lines = f_without.readlines()
    return list(zip(tsv_lines, parent_lines, without_lines))

def filter_origin(manifest, duration_threshold):
    filtered = []
    for i, (tsv_line, parent_line, without_line) in enumerate(manifest):
        fields = tsv_line.strip().split('\t')
        try:
            duration = int(fields[-1])
        except:
            raise
        if duration < duration_threshold:
            filtered.append((tsv_line, parent_line, without_line))
    return filtered

def filter_aligned(manifest):
    filtered = []
    for i, (tsv_line, parent_line, without_line) in enumerate(manifest):
        if without_line.strip() != "":
            filtered.append((tsv_line, parent_line, without_line))
    return filtered

def main(args):
    origin_manifest = load_manifest(
        f'{args.manifest_dir}/{args.split}.tsv',
        f'{args.manifest_dir}/{args.split}.wrd.with.parentheses',
        f'{args.manifest_dir}/{args.split}.wrd.without.parentheses'
    )
    aligned_manifest = load_manifest(
        f'{args.aligned_manifest_dir}/{args.split}.tsv',
        f'{args.aligned_manifest_dir}/{args.split}.wrd.with.parentheses',
        f'{args.aligned_manifest_dir}/{args.split}.wrd.without.parentheses'
    )

    origin_filtered = filter_origin(origin_manifest, duration_threshold=15*args.sr)
    aligned_filtered = filter_aligned(aligned_manifest)
    
    combined = origin_filtered + aligned_filtered
    random.shuffle(combined)

    os.makedirs(args.output_manifest_dir, exist_ok=True)

    with open(f'{args.output_manifest_dir}/{args.split}.tsv', 'w', encoding='utf-8') as f_tsv, \
        open(f'{args.output_manifest_dir}/{args.split}.wrd.with.parentheses', 'w', encoding='utf-8') as f_parent, \
        open(f'{args.output_manifest_dir}/{args.split}.wrd.without.parentheses', 'w', encoding='utf-8') as f_without:
        print("{}".format(args.split), file=f_tsv)
        for tsv_line, parent_line, without_line in combined:
            f_tsv.write(tsv_line)
            f_parent.write(parent_line)
            f_without.write(without_line)

    print(len(origin_manifest), len(origin_filtered))
    print(len(aligned_manifest), len(aligned_filtered))
    print(len(combined))

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)