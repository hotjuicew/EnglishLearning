import whisper
import subprocess
import pandas as pd
import os
from difflib import SequenceMatcher
from googletrans import Translator  # 自动翻译

# ===================== 1. 读取 `english.txt` =====================
def load_english_text(english_file):
    print("📄 读取 `english.txt` 作为一整段文本...")
    with open(english_file, "r", encoding="utf-8") as f:
        english_text = f.read().replace("\n", " ").replace("  ", "")  # **整合为一整段文本**
    
    print(f"✅ 加载完成，总字符数：{len(english_text)}")
    return english_text

# ===================== 2. 运行 Whisper 识别音频（优化断句） =====================
def transcribe_audio(audio_file):
    print("🔍 运行 Whisper 识别完整音频（减少断句频率）...")
    model = whisper.load_model("medium")

    result = model.transcribe(
        audio_file,
        word_timestamps=True,  
        language="en",
        temperature=0.1,  # 低温度，避免乱断句
        best_of=5,  
        compression_ratio_threshold=4.0,  # 提高压缩比，减少断句
        no_speech_threshold=0.5,  # 忽略短暂停顿
        logprob_threshold=-2.0,  # 允许更低置信度的句子，不要强行分段
        condition_on_previous_text=False  # 让 Whisper 只考虑当前句子，减少短句
    )

    whisper_sentences = [seg["text"] for seg in result["segments"]]
    timestamps = [(seg["start"], seg["end"]) for seg in result["segments"]]

    print(f"✅ Whisper 识别完成，生成 {len(whisper_sentences)} 句")
    return whisper_sentences, timestamps

# ===================== 3. 合并短句 =====================
def merge_short_sentences(whisper_sentences, timestamps, min_duration=0.5, max_merge=3):
    print("🔄 合并短句，减少断句...")
    merged_sentences = []
    merged_timestamps = []

    i = 0
    while i < len(whisper_sentences):
        current_sentence = whisper_sentences[i]
        start_time = timestamps[i][0]
        end_time = timestamps[i][1]
        merge_count = 0  # 记录合并次数，避免超限

        # 如果下一个句子的间隔很短，就合并
        while (
            i + 1 < len(whisper_sentences) and 
            (timestamps[i + 1][0] - end_time) < min_duration and 
            merge_count < max_merge  # 限制最大合并次数
        ):
            current_sentence += " " + whisper_sentences[i + 1]
            end_time = timestamps[i + 1][1]
            i += 1  # 跳过合并的句子
            merge_count += 1  # 计数

        merged_sentences.append(current_sentence)
        merged_timestamps.append((start_time, end_time))
        i += 1  # 移动到下一个未合并的句子

    print(f"✅ 合并完成，最终保留 {len(merged_sentences)} 句")
    return merged_sentences, merged_timestamps


# ===================== 4. 智能匹配 `english.txt` 句子 =====================
def match_text_with_whisper(whisper_sentences, english_text):
    print("🔄 根据 Whisper 分句匹配 `english.txt` 内容...")
    matched_english = []

    for whisper_sentence in whisper_sentences:
        best_match_index = max(
            range(len(english_text) - len(whisper_sentence)),
            key=lambda i: SequenceMatcher(None, english_text[i:i+len(whisper_sentence)], whisper_sentence).ratio()
        )
        best_match_english = english_text[best_match_index:best_match_index+len(whisper_sentence)]
        matched_english.append(best_match_english)

    print(f"✅ 匹配完成，共 {len(matched_english)} 句")
    return matched_english

# ===================== 5. 自动翻译英文到中文 =====================
def translate_to_chinese(english_sentences):
    print("🌍 自动翻译 `english.txt` 句子到中文...")
    translator = Translator()
    chinese_sentences = []

    for sentence in english_sentences:
        translation = translator.translate(sentence, src="en", dest="zh-cn").text
        chinese_sentences.append(translation)
        print(f"🔹 {sentence} → {translation}")

    print(f"✅ 翻译完成，共 {len(chinese_sentences)} 句")
    return chinese_sentences

# ===================== 6. 使用 FFmpeg 裁剪音频 =====================
def split_audio(audio_file, timestamps, output_folder="audio_clips"):
    print("✂️  开始剪辑音频...")
    os.makedirs(output_folder, exist_ok=True)
    audio_files = []

    for i, (start, end) in enumerate(timestamps):
        output_file = f"{output_folder}/{audio_file.replace('.mp3', '')}_{i+1}.mp3"
        command = f'ffmpeg -i "{audio_file}" -ss {start} -to {end} -q:a 0 -map a "{output_file}" -y'
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio_files.append(output_file)
        print(f"🎧 剪辑完成：{output_file}")

    print(f"✅ 所有音频剪辑完成，共 {len(audio_files)} 句")
    return audio_files

# ===================== 7. 生成 Anki CSV 文件 =====================
def create_anki_csv(matched_english, chinese_sentences, audio_files, output_csv="anki_listening_deck.csv"):
    print("📄  生成 Anki CSV 文件...")
    
    data = [
        ("[sound:" + os.path.basename(audio) + "]", english_text + "<br><br>" + chinese_text)
        for english_text, chinese_text, audio in zip(matched_english, chinese_sentences, audio_files)
    ]

    df = pd.DataFrame(data, columns=["Front", "Back"])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ Anki CSV 文件已生成：{output_csv}")
    return output_csv

# ===================== 8. 主程序执行 =====================
def main():
    audio_file = "托福真题36Passage1.mp3"  
    english_file = "english.txt"  
    output_folder = "audio_clips"

    print(f"⚠️ 即将处理音频文件：{audio_file}")
    confirm = input("是否继续？(Y/N): ").strip().lower()

    if confirm != "y":
        print("❌ 任务已取消。")
        return

    print("✅ 确认继续，开始处理音频...")

    # 读取 `english.txt` 作为一整段
    english_text = load_english_text(english_file)

    # 运行 Whisper，获取时间戳
    whisper_sentences, timestamps = transcribe_audio(audio_file)

    # 合并短句，减少断句
    merged_sentences, merged_timestamps = merge_short_sentences(whisper_sentences, timestamps)

    # 根据 Whisper 识别的分句，在 `english.txt` 里找到最匹配的内容
    matched_english = match_text_with_whisper(merged_sentences, english_text)

    # 自动翻译成中文
    chinese_sentences = translate_to_chinese(matched_english)

    # 裁剪音频
    audio_files = split_audio(audio_file, merged_timestamps, output_folder)

    # 生成 Anki CSV
    csv_file = create_anki_csv(matched_english, chinese_sentences, audio_files)

if __name__ == "__main__":
    main()
