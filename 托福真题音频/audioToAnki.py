from faster_whisper import WhisperModel
import subprocess
import pandas as pd
import os
from difflib import SequenceMatcher

# ===================== 1. 读取完整听力文本 =====================
def load_full_text(text_file):
    print("📄 读取完整听力文本...")
    english_sentences = []
    chinese_sentences = []

    with open(text_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    for i in range(0, len(lines), 2):  # 每两行是一组（英文 + 中文）
        if i + 1 < len(lines):
            english_sentences.append(lines[i])
            chinese_sentences.append(lines[i + 1])

    print(f"✅ 加载完成：英文 {len(english_sentences)} 句，中文 {len(chinese_sentences)} 句")
    return english_sentences, chinese_sentences

# ===================== 2. 运行 Whisper 获取逐词时间戳 =====================
def transcribe_audio(audio_file):
    print("🔍 运行 Faster-Whisper 识别完整音频（获取每个单词的时间戳）...")
    model = WhisperModel("medium", compute_type="int8")

    segments, _ = model.transcribe(audio_file, vad_filter=True)  # 使用语音活动检测
    whisper_sentences = []
    timestamps = []

    for segment in segments:
        whisper_sentences.append(segment.text.strip())
        timestamps.append((segment.start, segment.end))

    print(f"✅ Whisper 识别完成，生成 {len(whisper_sentences)} 个片段")
    return whisper_sentences, timestamps

# ===================== 3. 用 `full_text.txt` 对齐 Whisper 识别的时间戳 =====================
def align_sentences(whisper_sentences, whisper_timestamps, full_text_sentences, whisper_results):
    print("🔄 正在匹配 `full_text.txt` 句子...")
    aligned_timestamps = []

    for i, full_text in enumerate(full_text_sentences):
        best_match_index = max(
            range(len(whisper_sentences)),
            key=lambda j: SequenceMatcher(None, whisper_sentences[j], full_text).ratio()
        )

        # 计算该句子的单词时间戳
        words = whisper_results["segments"][best_match_index]["words"]
        if words:
            start_time = words[0]["start"]
            end_time = words[-1]["end"]
        else:
            start_time, end_time = whisper_timestamps[best_match_index]

        # 进行平滑处理，避免时间戳出现在上一句或下一句
        if i > 0:
            prev_end = aligned_timestamps[i - 1][1]
            start_time = max(start_time, prev_end + 0.1)  # 避免时间重叠
        if i < len(full_text_sentences) - 1:
            next_start = whisper_timestamps[min(best_match_index + 1, len(whisper_timestamps) - 1)][0]
            end_time = min(end_time, next_start - 0.1)

        aligned_timestamps.append((start_time, end_time))

    print(f"✅ 对齐完成，所有 `full_text.txt` 句子已匹配对应时间戳")
    return aligned_timestamps

# ===================== 4. 使用 FFmpeg 裁剪音频 =====================
def split_audio(audio_file, timestamps, output_folder="audio_clips"):
    print("✂️  开始剪辑音频...")
    os.makedirs(output_folder, exist_ok=True)
    audio_files = []

    for i, (start, end) in enumerate(timestamps):
        output_file = f"{output_folder}/sentence_{i+1}.mp3"
        command = f'ffmpeg -i "{audio_file}" -ss {start} -to {end} -q:a 0 -map a "{output_file}" -y'
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio_files.append(output_file)
        print(f"🎧 剪辑完成：{output_file}")

    print(f"✅ 所有音频剪辑完成，共 {len(audio_files)} 句")
    return audio_files

# ===================== 5. 生成 Anki CSV 文件 =====================
def create_anki_csv(english_sentences, chinese_sentences, audio_files, output_csv="anki_listening_deck.csv"):
    print("📄  生成 Anki CSV 文件...")
    
    data = [
        ("[sound:" + os.path.basename(audio) + "]", english + "<br><br>" + chinese)
        for english, chinese, audio in zip(english_sentences, chinese_sentences, audio_files)
    ]

    df = pd.DataFrame(data, columns=["Front", "Back"])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ Anki CSV 文件已生成：{output_csv}")
    return output_csv

# ===================== 6. 主程序执行 =====================
def main():
    audio_file = "托福100真题3L2.mp3"
    text_file = "full_text.txt"
    output_folder = "audio_clips"

    # 读取完整文本
    english_sentences, chinese_sentences = load_full_text(text_file)

    # 运行 Whisper，获取完整音频 + 逐词时间戳
    whisper_sentences, whisper_timestamps, whisper_results = transcribe_audio(audio_file)

    # 让 `whisper_timestamps` 对齐 `full_text.txt`
    aligned_timestamps = align_sentences(whisper_sentences, whisper_timestamps, english_sentences, whisper_results)

    # 裁剪音频
    audio_files = split_audio(audio_file, aligned_timestamps, output_folder)

    # 生成 Anki CSV
    csv_file = create_anki_csv(english_sentences, chinese_sentences, audio_files)

    print("\n🚀 **所有任务完成！请将以下文件导入 Anki：**")
    print(f"📂 {csv_file} （卡片数据）")
    print(f"📂 {output_folder}/  （所有音频文件，需放入 Anki media 目录）")

if __name__ == "__main__":
    main()
