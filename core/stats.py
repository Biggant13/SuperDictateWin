import os
import json
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_PATH = os.path.join(BASE_DIR, "stats.json")

def load_stats():
    today_str = str(date.today())
    if not os.path.exists(STATS_PATH):
        return {"total_words": 0, "today_words": 0, "date": today_str}
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            stats = json.load(f)
            # Миграция со старого формата (если не было today_words)
            if "today_words" not in stats:
                stats["today_words"] = 0
            if "date" not in stats:
                stats["date"] = today_str
            return stats
    except:
        return {"total_words": 0, "today_words": 0, "date": today_str}

def add_words(count):
    stats = load_stats()
    today_str = str(date.today())
    
    # Если наступил новый день, сбрасываем сегодняшний счетчик
    if stats.get("date") != today_str:
        stats["date"] = today_str
        stats["today_words"] = 0
        
    stats["total_words"] += count
    stats["today_words"] += count
    
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"[Stats] Ошибка сохранения: {e}")

def _format_time(words):
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

def get_stats_text():
    stats = load_stats()
    today_str = str(date.today())
    
    # Если день сменился (например, программа работала ночью), не показываем вчерашние цифры
    today_words = stats.get("today_words", 0) if stats.get("date") == today_str else 0
    total_words = stats.get("total_words", 0)
    
    today_text = f"📅 Сегодня: {_format_time(today_words)}"
    total_text = f"🏆 Всего: {_format_time(total_words)}"
    
    return today_text, total_text