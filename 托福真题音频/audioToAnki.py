import whisper
import subprocess
import pandas as pd
import os
from difflib import SequenceMatcher

# ===================== 1. 读取完整听力文本 =====================
def load_text(english_file, chinese_file):
    print("📄 读取完整听力文本...")
    
    with open(english_file, "r", encoding="utf-8") as f:
        english_text = f.read().replace("\n", " ")  # **不再按换行分句，整合成一个长文本**

    with open(chinese_file, "r", encoding="utf-8") as f:
        chinese_text = f.read().replace("\n", " ")  # **整合成一个长文本**

    print(f"✅ 加载完成：英文 {len(english_text)} 字符，中文 {len(chinese_text)} 字符")
    return english_text, chinese_text

# ===================== 2. 运行 Whisper 识别音频（优化参数） =====================
def transcribe_audio(audio_file):
    print("🔍 运行 Whisper 识别完整音频（优化分句，让每句话尽量长）...")
    model = whisper.load_model("medium")

    result = model.transcribe(
        audio_file,
        word_timestamps=True,  
        language="en",
        temperature=0.0,
        best_of=5,  # 选择最好的结果，避免短句
        compression_ratio_threshold=3.5,  # 防止过度断句
        no_speech_threshold=0.3,  # 允许一定的无声时间，减少不必要的拆分
        logprob_threshold=-1.0  # 降低门槛，确保完整句子
    )

    whisper_sentences = [seg["text"] for seg in result["segments"]]
    timestamps = [(seg["start"], seg["end"]) for seg in result["segments"]]

    print(f"✅ Whisper 识别完成，生成 {len(whisper_sentences)} 句")
    return whisper_sentences, timestamps

# ===================== 3. 匹配 Whisper 结果和 `english.txt` `chinese.txt` =====================
def match_texts(whisper_sentences, english_text, chinese_text):
    print("🔄 正在匹配 `whisper_sentences` 句子...")

    matched_english = []
    matched_chinese = []

    for whisper_sentence in whisper_sentences:
        # 找到 `english_text` 里最匹配的片段
        best_match_index = max(
            range(len(english_text) - len(whisper_sentence)),
            key=lambda i: SequenceMatcher(None, english_text[i:i+len(whisper_sentence)], whisper_sentence).ratio()
        )
        best_match_english = english_text[best_match_index:best_match_index+len(whisper_sentence)]

        # **找到对应的中文翻译**
        best_match_chinese_index = max(
            range(len(chinese_text) - len(best_match_english)),
            key=lambda i: SequenceMatcher(None, chinese_text[i:i+len(best_match_english)], best_match_english).ratio()
        )
        best_match_chinese = chinese_text[best_match_chinese_index:best_match_chinese_index+len(best_match_english)]

        matched_english.append(best_match_english)
        matched_chinese.append(best_match_chinese)

    print(f"✅ 匹配完成，所有 `whisper_sentences` 均找到对应文本")
    return matched_english, matched_chinese

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
def create_anki_csv(whisper_sentences, matched_english, matched_chinese, audio_files, output_csv="anki_listening_deck.csv"):
    print("📄  生成 Anki CSV 文件...")
    
    data = [
        ("[sound:" + os.path.basename(audio) + "]", whisper_text + "<br><br>" + english_text + "<br><br>" + chinese_text)
        for whisper_text, english_text, chinese_text, audio in zip(whisper_sentences, matched_english, matched_chinese, audio_files)
    ]

    df = pd.DataFrame(data, columns=["Front", "Back"])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ Anki CSV 文件已生成：{output_csv}")
    return output_csv

# ===================== 6. 主程序执行 =====================
def main():
    audio_file = "托福真题35Passage2.mp3"  # 你的托福听力音频
    english_file = "english.txt"  # 你的完整英文文本
    chinese_file = "chinese.txt"  # 你的完整中文文本
    output_folder = "audio_clips"

    # 读取完整文本（不按换行拆分）
    english_text, chinese_text = load_text(english_file, chinese_file)

    # 运行 Whisper，获取完整音频 + 逐词时间戳
    whisper_sentences, timestamps = transcribe_audio(audio_file)

    # 让 `whisper_sentences` 对齐 `english.txt` 和 `chinese.txt`
    matched_english, matched_chinese = match_texts(whisper_sentences, english_text, chinese_text)

    # 裁剪音频
    audio_files = split_audio(audio_file, timestamps, output_folder)

    # 生成 Anki CSV
    csv_file = create_anki_csv(whisper_sentences, matched_english, matched_chinese, audio_files)

    print("\n🚀 **所有任务完成！请将以下文件导入 Anki：**")
    print(f"📂 {csv_file} （卡片数据）")
    print(f"📂 {output_folder}/  （所有音频文件，需放入 Anki media 目录）")

if __name__ == "__main__":
    main()
