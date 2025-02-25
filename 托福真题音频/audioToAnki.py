import whisper
import subprocess
import pandas as pd
import os
import re
from difflib import SequenceMatcher

# ===================== 1. 读取完整听力文本（提取英文和中文） =====================
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

# ===================== 2. 运行 Whisper 获取时间戳 =====================
def transcribe_audio(audio_file, english_sentences):
    print("🔍 运行 Whisper 获取时间戳（强制匹配英文文本）...")
    model = whisper.load_model("medium")

    result = model.transcribe(
        audio_file,
        word_timestamps=True,
        language="en",
        initial_prompt="\n".join(english_sentences),  # 让 Whisper 参考完整英文文本
        temperature=0.0,
        compression_ratio_threshold=3.0
    )

    whisper_sentences = [seg["text"] for seg in result["segments"]]
    timestamps = [(seg["start"], seg["end"]) for seg in result["segments"]]

    # 确保 Whisper 识别出的文本和 `full_text.txt` 进行对齐
    aligned_sentences = align_sentences(whisper_sentences, english_sentences)

    print(f"✅ 获取时间戳完成，共 {len(timestamps)} 段")
    return timestamps[:len(aligned_sentences)], aligned_sentences

# ===================== 3. 匹配 Whisper 句子和 `full_text.txt` =====================
def align_sentences(whisper_sentences, full_text_sentences):
    aligned_sentences = []
    
    for full_text in full_text_sentences:
        best_match = max(whisper_sentences, key=lambda x: SequenceMatcher(None, x, full_text).ratio())
        aligned_sentences.append(best_match)

    return aligned_sentences

# ===================== 4. 使用 FFmpeg 裁剪音频 =====================
def split_audio(audio_file, timestamps, output_folder="audio_clips"):
    print("✂️  开始剪辑音频...")
    os.makedirs(output_folder, exist_ok=True)
    audio_files = []

    for i, (start, end) in enumerate(timestamps):
        output_file = f"{output_folder}/{audio_file}_{i+1}.mp3"
        command = f'ffmpeg -i "{audio_file}" -ss {start} -to {end} -q:a 0 -map a "{output_file}" -y'
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio_files.append(output_file)
        print(f"🎧 剪辑完成：{output_file}")

    print(f"✅ 所有音频剪辑完成，共 {len(audio_files)} 句")
    return audio_files

# ===================== 5. 生成 Anki CSV 文件 =====================
def create_anki_csv(english_sentences, chinese_sentences, audio_files, output_csv="anki_listening_deck.csv"):
    print("📄  生成 Anki CSV 文件...")
    
    # 正面是音频，背面是英文 + 中文翻译
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
    audio_file = "托福100真题3C1.mp3"
    text_file = "full_text.txt"
    output_folder = "audio_clips"

    # 读取完整文本（提取英文和中文）
    english_sentences, chinese_sentences = load_full_text(text_file)

    # 运行 Whisper 获取时间戳，并匹配完整英文文本
    timestamps, aligned_sentences = transcribe_audio(audio_file, english_sentences)

    # 确保时间戳和文本匹配
    if len(aligned_sentences) != len(timestamps):
        print(f"⚠️ 警告：文本句数 ({len(aligned_sentences)}) 与 Whisper 识别的时间戳数 ({len(timestamps)}) 不匹配！")
        print("🔍 请检查 full_text.txt 是否与音频对应，或手动调整时间戳！")
        return

    # 裁剪音频
    audio_files = split_audio(audio_file, timestamps, output_folder)

    # 生成 Anki CSV
    csv_file = create_anki_csv(english_sentences, chinese_sentences, audio_files)

    print("\n🚀 **所有任务完成！请将以下文件导入 Anki：**")
    print(f"📂 {csv_file} （卡片数据）")
    print(f"📂 {output_folder}/  （所有音频文件，需放入 Anki media 目录）")

if __name__ == "__main__":
    main()
