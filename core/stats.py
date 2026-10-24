import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_PATH = os.path.join(BASE_DIR, "stats.json")

def load_stats():
    if not os.path.exists(STATS_PATH):
        return {"total_words": 0}
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"total_words": 0}

def add_words(count):
    stats = load_stats()
    stats["total_words"] += count
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"[Stats] Ошибка сохранения: {e}")

def get_stats_text():
    stats = load_stats()
    words = stats["total_words"]
    if words == 0:
        return "0 слов"
    
    # 40 слов в минуту = 1.5 секунды на слово
    seconds = int(words * 1.5)
    
    if seconds < 60:
        return f"{words} слов (~{seconds} сек)"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{words} слов (~{minutes} мин)"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{words} слов (~{hours}ч {minutes}м)"