import csv
import argparse, os

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--manifest-dir", default="../manifest", type=str, metavar="DATA_PTH", help="data_pth"
    )
    parser.add_argument(
        "--manifest-type", default="aligned", type=str, metavar="DATA_PTH", help="data_pth"
    )
    return parser

def main(args):
    tsv_file_path = f'{args.manifest_dir}/{args.manifest_type}/{args.split}.tsv'
    wrd_with_path = f'{args.manifest_dir}/{args.manifest_type}/{args.split}.wrd.with.parentheses'
    wrd_without_path = f'{args.manifest_dir}/{args.manifest_type}/{args.split}.wrd.without.parentheses'
    os.makedirs(f'./{args.manifest_type}/', exist_ok=True)
    output_csv_path = f'./{args.manifest_type}/{args.split}.csv'

    with open(tsv_file_path, 'r', encoding='utf-8') as tsv_file, \
        open(wrd_with_path, 'r', encoding='utf-8') as wrd_with_file, \
        open(wrd_without_path, 'r', encoding='utf-8') as wrd_without_file, \
        open(output_csv_path, 'w', encoding='utf-8', newline='') as csv_file:
        
        writer = csv.writer(csv_file)
        next(tsv_file)

        for tsv_line, with_line, without_line in zip(tsv_file, wrd_with_file, wrd_without_file):
            tsv_columns = tsv_line.strip().split('\t')
            col1 = tsv_columns[0] if tsv_columns else ''
            
            col_with = with_line.strip()
            col_without = without_line.strip()
            
            writer.writerow([col1, col_with, col_without])

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
