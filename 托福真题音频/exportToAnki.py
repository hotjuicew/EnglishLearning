import os
import shutil
import json
import requests

ANKI_MEDIA_FOLDER = os.path.expanduser(r"C:\Users\Jasmine\AppData\Roaming\Anki2\账户 1\collection.media")
CSV_FILE = "anki_listening_deck.csv"
AUDIO_FOLDER = "audio_clips"
ANKI_CONNECT_URL = "http://localhost:8765"

def copy_audio_files():
    """复制音频文件到 Anki `collection.media` 目录"""
    print("📂 复制音频文件到 Anki...")
    if not os.path.exists(ANKI_MEDIA_FOLDER):
        print(f"❌ 找不到 Anki 媒体目录：{ANKI_MEDIA_FOLDER}")
        return

    for file in os.listdir(AUDIO_FOLDER):
        src_path = os.path.join(AUDIO_FOLDER, file)
        dest_path = os.path.join(ANKI_MEDIA_FOLDER, file)
        shutil.copy(src_path, dest_path)
        print(f"✅ 复制：{file}")

def import_csv_to_anki():
    """使用 AnkiConnect API 导入 CSV"""
    print("📂 正在导入 CSV 到 Anki...")
    
    # 读取 CSV 文件
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]  # 跳过表头
    
    notes = []
    for line in lines:
        front, back = line.strip().split(",", 1)
        notes.append({
            "deckName": "托福真题听力句子::托福真题37",
            "modelName": "问答题",
            "fields": {"正面": front, "背面": back},
            "tags": ["AutoImported"],
            "options": {"allowDuplicate": False},
            "audio": [{"filename": front.replace("[sound:", "").replace("]", ""), "fields": ["Front"]}]
        })

    # 发送请求给 AnkiConnect
    payload = {
        "action": "addNotes",
        "version": 6,
        "params": {"notes": notes}
    }
    
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    
    if "error" in response and response["error"]:
        print(f"❌ 导入错误：{response['error']}")
    else:
        print("✅ CSV 导入完成！")

def main():
    copy_audio_files()
    import_csv_to_anki()
    print("🎉 所有任务完成！请打开 Anki 查看结果！")

if __name__ == "__main__":
    main()
