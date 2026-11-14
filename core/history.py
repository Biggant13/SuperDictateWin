import os
import json
import tkinter as tk
from tkinter import messagebox
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
    history.insert(0, text.strip())
    history = history[:MAX_RECORDS]
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[History] Ошибка сохранения: {e}")

# --- НОВАЯ ФУНКЦИЯ ОЧИСТКИ ---
def clear_history():
    """Полностью очищает историю."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception as e:
        print(f"[History] Ошибка очистки: {e}")

def open_history_window(root):
    """Открывает окно со списком распознаваний."""
    history = load_history()
    
    win = tk.Toplevel(root)
    win.title("История распознаваний")
    
    # Позиционирование в правом нижнем углу
    window_width = 500
    window_height = 520 
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = screen_width - window_width - 40
    y = screen_height - window_height - 80
    win.geometry(f"{window_width}x{window_height}+{x}+{y}")
    win.attributes("-topmost", True)
    
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
    
    text_widget = tk.Text(
        frame, 
        wrap=tk.WORD, 
        yscrollcommand=scrollbar.set,
        bg="#2b2b2b", fg=fg_color,
        font=("Segoe UI", 10),
        borderwidth=0, highlightthickness=0,
        cursor="hand2",
        padx=10, pady=10
    )
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    text_widget.tag_configure("item", spacing1=5, spacing3=5, lmargin1=5, lmargin2=5)
    
    # Заполняем текст
    for i, item in enumerate(history):
        tag_name = f"item_{i}"
        text_widget.insert(tk.END, item + "\n", ("item", tag_name))
        
        # Твои 25 символов
        text_widget.insert(tk.END, "─" * 25 + "\n", ("separator",))

    text_widget.tag_configure("separator", foreground="#555555", justify="center")
    text_widget.config(state=tk.DISABLED)

    # Логика клика
    def on_click(event):
        index = text_widget.index(f"@{event.x},{event.y}")
        tags = text_widget.tag_names(index)
        
        for tag in tags:
            if tag.startswith("item_"):
                idx = int(tag.split("_")[1])
                pyperclip.copy(history[idx])
                win.title("История распознаваний (Скопировано!)")
                win.after(1500, lambda: win.title("История распознаваний"))
                break

    text_widget.bind("<ButtonRelease-1>", on_click)

    # --- НОВАЯ ЛОГИКА ДЛЯ КНОПКИ ОЧИСТКИ ---
    def on_clear():
        if messagebox.askyesno("Очистка", "Вы уверены, что хотите удалить всю историю?", parent=win):
            clear_history()
            history.clear()
            # Очищаем сам виджет
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.config(state=tk.DISABLED)
            win.title("История распознаваний (Очищено!)")
            win.after(1500, lambda: win.title("История распознаваний"))

    # Кнопка очистки в самом низу окна
    btn_clear = tk.Button(
        win, 
        text="🗑 Очистить историю", 
        command=on_clear, 
        bg="#f44336", fg="white", 
        font=("Segoe UI", 9, "bold"), 
        relief="flat", cursor="hand2"
    )
    btn_clear.pack(side=tk.BOTTOM, pady=10)
