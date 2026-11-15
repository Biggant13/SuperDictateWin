import os
import json
import tkinter as tk
from tkinter import messagebox
import pyperclip
from core.config import BASE_DIR

HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
MAX_RECORDS = 100  # Храним последние 100 записей

def _save_history(history):
    """Атомарно сохраняет историю в файл."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[History] Ошибка сохранения: {e}")


def _migrate_entry(item):
    """Приводит запись любого формата к {'text': str, 'favorite': bool}."""
    if isinstance(item, str):
        return {"text": item, "favorite": False}
    if isinstance(item, dict) and "text" in item:
        return {
            "text": str(item.get("text", "")),
            "favorite": bool(item.get("favorite", False)),
        }
    return None

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            normalized = _migrate_entry(item)
            if normalized is not None:
                result.append(normalized)
        return result
    except Exception:
        return []

def add_record(text):
    """Сохраняет новый текст в историю."""
    if not text or not text.strip():
        return
    history = load_history()
    history.insert(0, {"text": text.strip(), "favorite": False})
    if len(history) > MAX_RECORDS:
        favorites = [h for h in history if h.get("favorite", False)]
        regular = [h for h in history if not h.get("favorite", False)]
        # Оставляем все избранные + столько обычных, сколько влезет в лимит
        slots_left = max(0, MAX_RECORDS - len(favorites))
        history = favorites + regular[:slots_left]
        # Восстанавливаем хронологический порядок (новые сверху)
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    _save_history(history)

# --- НОВАЯ ФУНКЦИЯ ОЧИСТКИ ---
def clear_history():
    """Очищает историю, сохраняя избранные записи."""
    history = load_history()
    favorites = [h for h in history if h.get("favorite", False)]
    _save_history(favorites)

def open_history_window(root):
    """Открывает окно со списком распознаваний."""
    history = load_history()
    state = {"filter_favorites": False}

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

    bg_color = "#1e1e1e"
    fg_color = "#ffffff"
    win.configure(bg=bg_color)

    lbl = tk.Label(
        win,
        text="★ — в избранное · 🗑 — удалить · клик по тексту — скопировать",
        bg=bg_color, fg=fg_color, font=("Segoe UI", 9),
    )
    lbl.pack(pady=5)

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
        padx=10, pady=10,
    )
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    text_widget.tag_configure("item", spacing1=5, spacing3=5, lmargin1=5, lmargin2=5)
    text_widget.tag_configure("fav_bg", background="#fff59d", foreground="#000000")
    text_widget.tag_configure("separator", foreground="#555555", justify="center")
    text_widget.tag_configure("empty", foreground="#888888", justify="center", spacing1=20)
    # ВАЖНО: эти теги созданы ПОСЛЕ fav_bg — их foreground имеет приоритет
    text_widget.tag_configure("star_on", foreground="#e65100")
    text_widget.tag_configure("star_off", foreground="#888888")

    def render():
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)

        visible = [
            (i, item) for i, item in enumerate(history)
            if not state["filter_favorites"] or item.get("favorite", False)
        ]

        if not visible:
            msg = "Нет избранных записей" if state["filter_favorites"] else "История пуста"
            text_widget.insert(tk.END, msg + "\n", ("empty",))
        else:
            for i, item in visible:
                is_fav = item.get("favorite", False)
                row_tags = ["item", "fav_bg"] if is_fav else ["item"]
                star_char = "★" if is_fav else "☆"
                star_tag = "star_on" if is_fav else "star_off"
                text_widget.insert(tk.END, star_char + " ",
                                   (f"favtoggle_{i}", star_tag, *row_tags))
                text_widget.insert(tk.END, item["text"], (f"item_{i}", *row_tags))
                text_widget.insert(tk.END, " ", tuple(row_tags))
                text_widget.insert(tk.END, "🗑", (f"trash_{i}", *row_tags))
                text_widget.insert(tk.END, "\n", tuple(row_tags))
                text_widget.insert(tk.END, "─" * 25 + "\n", ("separator",))

        text_widget.config(state=tk.DISABLED)

    def on_click(event):
        index = text_widget.index(f"@{event.x},{event.y}")
        tags = text_widget.tag_names(index)

        # Приоритет: звезда > мусорка > копирование
        for tag in tags:
            if tag.startswith("favtoggle_"):
                idx = int(tag.split("_")[1])
                history[idx]["favorite"] = not history[idx].get("favorite", False)
                _save_history(history)
                render()
                return
        for tag in tags:
            if tag.startswith("trash_"):
                try:
                    idx = int(tag.rsplit("_", 1)[1])
                except (ValueError, IndexError):
                    continue
                del history[idx]
                _save_history(history)
                render()
                return
        for tag in tags:
            if tag.startswith("item_"):
                idx = int(tag.split("_")[1])
                pyperclip.copy(history[idx]["text"])
                win.title("История распознаваний (Скопировано!)")
                win.after(1500, lambda: win.title("История распознаваний"))
                return

    text_widget.bind("<ButtonRelease-1>", on_click)

    def on_toggle_filter():
        state["filter_favorites"] = not state["filter_favorites"]
        btn_filter.config(
            text="★ Все записи" if state["filter_favorites"] else "★ Только избранные"
        )
        render()

    def on_clear():
        if not history:
            return
        fav_count = sum(1 for h in history if h.get("favorite", False))
        if fav_count > 0:
            msg = (
                f"Удалить все обычные записи?\n"
                f"Избранные ({fav_count}) останутся."
            )
        else:
            msg = "Вы уверены, что хотите удалить всю историю?"
        if not messagebox.askyesno("Очистка", msg, parent=win):
            return
        history[:] = [h for h in history if h.get("favorite", False)]
        _save_history(history)
        render()
        win.title("История распознаваний (Очищено!)")
        win.after(1500, lambda: win.title("История распознаваний"))

    btn_frame = tk.Frame(win, bg=bg_color)
    btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    btn_filter = tk.Button(
        btn_frame,
        text="★ Только избранные",
        command=on_toggle_filter,
        bg="#ffa726", fg="white",
        font=("Segoe UI", 9, "bold"),
        relief="flat", cursor="hand2",
    )
    btn_filter.pack(side=tk.LEFT, padx=5)

    btn_clear = tk.Button(
        btn_frame,
        text="🗑 Очистить историю",
        command=on_clear,
        bg="#f44336", fg="white",
        font=("Segoe UI", 9, "bold"),
        relief="flat", cursor="hand2",
    )
    btn_clear.pack(side=tk.RIGHT, padx=5)

    render()
