import os
import json
import tkinter as tk
import pyperclip
from core.config import BASE_DIR

HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
MAX_RECORDS = 100  # Храним последние 100 записей

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def add_record(text):
    """Сохраняет новый текст в историю."""
    if not text or not text.strip():
        return
    history = load_history()
    # Добавляем в начало списка
    history.insert(0, text.strip())
    # Обрезаем до лимита
    history = history[:MAX_RECORDS]
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[History] Ошибка сохранения: {e}")

def open_history_window(root):
    """Открывает окно со списком распознаваний."""
    history = load_history()
    
    win = tk.Toplevel(root)
    win.title("История распознаваний")
    win.geometry("500x400")
    win.attributes("-topmost", True)  # Окно поверх других
    
    # Тёмная тема
    bg_color = "#1e1e1e"
    fg_color = "#ffffff"
    win.configure(bg=bg_color)

    lbl = tk.Label(win, text="Нажми на текст, чтобы скопировать его:", bg=bg_color, fg=fg_color, font=("Segoe UI", 10))
    lbl.pack(pady=5)

    # Список с прокруткой
    frame = tk.Frame(win, bg=bg_color)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(
        frame, 
        yscrollcommand=scrollbar.set,
        bg="#2b2b2b", fg=fg_color,
        font=("Segoe UI", 10),
        selectbackground="#4caf50",
        borderwidth=0, highlightthickness=0
    )
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)

    for item in history:
        # Заменяем переносы строк на пробелы для красивого отображения в одну строку
        display_text = item.replace("\n", " ")
        listbox.insert(tk.END, display_text)

    def on_select(event):
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            pyperclip.copy(history[index])
            # Можно добавить всплывающее уведомление, но пока просто меняем заголовок
            win.title("История распознаваний (Скопировано!)")
            win.after(1500, lambda: win.title("История распознаваний"))

    listbox.bind("<<ListboxSelect>>", on_select)