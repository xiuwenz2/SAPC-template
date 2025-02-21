import difflib, os, argparse, re, multiprocessing
import soundfile as sf
from tqdm import tqdm

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="split"
    )
    parser.add_argument(
        "--data-dir", default="./", type=str, metavar="DATA-DIR", help="data dir"
    )
    parser.add_argument(
        "--manifest-dir", default="../manifest/origin", type=str, metavar="MANIFEST-DIR", help="manifest dir"
    )
    return parser

def get_json(manifest_dir, split):
    results = {}
    tsv_path = os.path.join(manifest_dir, f"{split}.tsv")
    wrd_with_path = os.path.join(manifest_dir, f"{split}.wrd.with.parentheses")
    wrd_without_path = os.path.join(manifest_dir, f"{split}.wrd.without.parentheses")
    
    with open(tsv_path, "r", encoding="utf-8") as f_tsv, \
         open(wrd_with_path, "r", encoding="utf-8") as f_wrd_with, \
         open(wrd_without_path, "r", encoding="utf-8") as f_wrd_without:
        
        next(f_tsv)
        tsv_lines = f_tsv.readlines()
        wrd_with_lines = f_wrd_with.readlines()
        wrd_without_lines = f_wrd_without.readlines()
        
        for tsv_line, with_line, without_line in zip(tsv_lines, wrd_with_lines, wrd_without_lines):
            fname = tsv_line.strip().split("\t")[0].split("/")[-1]
            wrd_with = with_line.strip()
            wrd_without = without_line.strip()
            
            results[fname[:-4]] = [wrd_with, wrd_without]
    
    return results

def extract_utterance_id(file_path):
    base = os.path.basename(file_path)
    idx = base.find("_segment")
    if idx != -1:
        return base[:idx]
    return None

def extract_segment_number(file_path):
    base = os.path.basename(file_path)
    m = re.search(r"_segment_(\d+)\.txt", base)
    if m:
        return int(m.group(1))
    return 0

def merge_apostrophe_tokens(text):
    tokens = text.split()
    if not tokens:
        return text
    merged_tokens = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.endswith("'") and i + 1 < len(tokens):
            token = token + tokens[i+1]
            i += 2
        else:
            i += 1
        if token.startswith("'") and merged_tokens:
            merged_tokens[-1] = merged_tokens[-1] + token
        else:
            merged_tokens.append(token)
    return " ".join(merged_tokens)

def load_segmented_tsv(segmented_tsv):
    groups = {}
    with open(segmented_tsv, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            file_path, seg_ref = parts[0], parts[1]
            utt_id = extract_utterance_id(file_path)
            if utt_id is None:
                print(f"Warning: 无法从 {file_path} 中提取 utterance id")
                continue
            seg_ref = merge_apostrophe_tokens(seg_ref)
            groups.setdefault(utt_id, []).append((file_path, seg_ref.upper()))
    
    for utt_id, items in groups.items():
        groups[utt_id] = sorted(items, key=lambda x: extract_segment_number(x[0]))
    return groups

def map_position(pos, matching_blocks):
    for i, j, n in matching_blocks:
        if i <= pos < i + n:
            return j + (pos - i)
    for i, j, n in matching_blocks:
        if pos < i:
            return j
    if matching_blocks:
        last_i, last_j, last_n = matching_blocks[-1]
        return last_j + last_n
    return None

def align_segments(full_ref, incomplete_ref, segments):
    mapped_segments = []
    search_start = 0
    for seg_text in segments:
        pos = full_ref.find(seg_text, search_start)
        if pos == -1:
            print(f"Warning: 无法在完整文本中找到分段: {seg_text}")
            mapped_segments.append("")
            continue
        seg_start = pos
        seg_end = pos + len(seg_text)
        search_start = seg_end

        sm = difflib.SequenceMatcher(None, full_ref, incomplete_ref)
        matching_blocks = sm.get_matching_blocks()
        mapped_start = map_position(seg_start, matching_blocks)
        mapped_end = map_position(seg_end, matching_blocks)
        if mapped_start is None or mapped_end is None:
            mapped_segments.append("")
        else:
            mapped_start = max(0, min(mapped_start, len(incomplete_ref)))
            mapped_end = max(mapped_start, min(mapped_end, len(incomplete_ref)))
            mapped_segments.append(incomplete_ref[mapped_start:mapped_end])
    return mapped_segments

def process_utt(args):
    utt_id, seg_items, content = args
    output_org_lines = []
    output_lines = []
    tsv_lines = []
    if utt_id not in content:
        print(f"Warning: {utt_id} 不在 content 中")
        for file_path, seg_ref in seg_items:
            output_org_lines.append(f"{file_path}\t{seg_ref}")
            output_lines.append(f"{file_path}\t")

            fname = file_path[1:-4]
            fname = f"./aligned{fname}.wav"
            tsv_lines.append(fname)
        return (utt_id, output_org_lines, output_lines, tsv_lines)
    
    full_ref, incomplete_ref = content[utt_id]
    seg_texts = [seg_ref for file_path, seg_ref in seg_items]
    mapped_segs = align_segments(full_ref, incomplete_ref, seg_texts)
    for (file_path, seg), mapped_seg in zip(seg_items, mapped_segs):
        output_org_lines.append(f"{file_path}\t{seg}")
        output_lines.append(f"{file_path}\t{mapped_seg}")

        fname = file_path[1:-4]
        fname = f"./aligned{fname}.wav"

        tsv_lines.append(fname)
    return (utt_id, output_org_lines, output_lines, tsv_lines)

def get_frames(fname):
    try:
        frames = sf.info(fname).frames
    except Exception as e:
        print(f"Warning: 无法获取 {fname} 的信息，错误: {e}")
        frames = 0
    return (fname, frames)

def process_segments(content, segmented_tsv, output_pth, args):
    groups = load_segmented_tsv(segmented_tsv)
    all_org_lines = []
    all_lines = []
    all_tsv_fnames = []
    
    tasks = [(utt_id, seg_items, content) for utt_id, seg_items in groups.items()]
    
    with multiprocessing.Pool() as pool:
        chunksize = max(1, len(tasks) // (pool._processes * 4))
        results = list(tqdm(pool.imap_unordered(process_utt, tasks, chunksize=chunksize), total=len(tasks)))
    
    for utt_id, org_lines, lines, tsv_fnames in sorted(results, key=lambda x: x[0]):
        all_org_lines.extend(org_lines)
        all_lines.extend(lines)
        all_tsv_fnames.extend(tsv_fnames)
    
    with multiprocessing.Pool() as pool:
        frames_results = list(tqdm(pool.imap(get_frames, all_tsv_fnames), total=len(all_tsv_fnames)))

    frames_dict = {fname: frames for fname, frames in frames_results}
    
    with open(f"{output_pth}.wrd.with.parentheses", 'w', encoding='utf-8') as fwrd1, \
         open(f"{output_pth}.wrd.without.parentheses", 'w', encoding='utf-8') as fwrd2, \
         open(f"{output_pth}.tsv", 'w', encoding='utf-8') as ftsv:
        print("{}".format(args.split), file=ftsv)

        for org_line, line, fname in tqdm(zip(all_org_lines, all_lines, all_tsv_fnames), total=len(all_org_lines)):
            print(org_line.split("\t")[-1], file=fwrd1)
            print(line.split("\t")[-1], file=fwrd2)
            frames = frames_dict.get(fname, 0)
            print(f"{fname}\t{frames}", file=ftsv)

def main(args):
    content = get_json(args.manifest_dir, args.split)
    segmented_tsv = f"./aligned/metadata/{args.split}.tsv"
    output_pth = f"./aligned/manifest/{args.split}"
    process_segments(content, segmented_tsv, output_pth, args)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
