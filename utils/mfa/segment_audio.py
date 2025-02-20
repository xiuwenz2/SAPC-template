import os, json, argparse
from tqdm import tqdm
from glob import glob
from pydub import AudioSegment
from multiprocessing import Pool

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", default="dev", type=str, metavar="SPLIT", help="name of split"
    )
    parser.add_argument(
        "--num_workers", default=4, type=int, metavar="SPLIT", help="name of split"
    )
    return parser

def process_file(json_file):
    try:
        base_name = os.path.splitext(os.path.basename(json_file))[0]
        
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        start_time = data.get("start")
        end_time = data.get("end")
        entries = data.get("tiers").get("words").get("entries")
        
        num_segments = int(end_time) // 15 + 1
        if num_segments < 1:
            num_segments = 1
        
        segment_duration = (end_time - start_time) / num_segments
        
        wav_file = os.path.join(processed_folder, base_name + ".wav")
        if not os.path.exists(wav_file):
            print(f"警告：{wav_file} 文件不存在，跳过")
            return
        
        audio = AudioSegment.from_wav(wav_file)
        
        for i in range(num_segments):
            seg_start = start_time + i * segment_duration
            seg_end = seg_start + segment_duration

            seg_start_ms = int(seg_start * 1000)
            seg_end_ms = int(seg_end * 1000)
            
            segment_audio = audio[seg_start_ms:seg_end_ms]
            
            seg_audio_filename = os.path.join(aligned_folder, f"{base_name}_segment_{i+1}.wav")
            segment_audio.export(seg_audio_filename, format="wav")
            
            segment_words = []
            for entry in entries:
                try:
                    word_end = float(entry[1])
                except Exception as e:
                    continue
                if seg_start <= word_end < seg_end:
                    segment_words.append(entry[2])
            
            seg_text_filename = os.path.join(aligned_folder, f"{base_name}_segment_{i+1}.txt")
            with open(seg_text_filename, "w", encoding="utf-8") as tf:
                tf.write(" ".join(segment_words))
            
            # print(f"已生成: {seg_audio_filename} 与 {seg_text_filename}")
    except Exception as e:
        print(f"处理 {json_file} 时发生错误：{e}")

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    mfa_folder = f"./mfa/{args.split}"
    processed_folder = f"./processed/{args.split}"
    aligned_folder = f"./aligned/{args.split}"

    os.makedirs(aligned_folder, exist_ok=True)

    json_files = glob(os.path.join(mfa_folder, "*.json"))

    with Pool(processes=args.num_workers) as pool:
        list(tqdm(pool.imap_unordered(process_file, json_files), total=len(json_files)))
        # pool.map(process_file, json_files)