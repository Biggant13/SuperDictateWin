import json
import tkinter as tk
from tkinter import ttk, messagebox
from core.config import CONFIG_PATH

def open_settings_window(root, current_cfg, on_save_callback):
    """Открывает окно настроек поверх остальных."""
    win = tk.Toplevel(root)
    win.title("Настройки SuperDictate")
    win.geometry("350x300")
    win.attributes("-topmost", True)
    win.resizable(False, False)

    # Центрируем окно
    win.update_idletasks()
    x = (win.winfo_screenwidth() - win.winfo_width()) // 2
    y = (win.winfo_screenheight() - win.winfo_height()) // 2
    win.geometry(f"+{x}+{y}")

    # --- Элементы ---
    tk.Label(win, text="Горячая клавиша (напр. f9):", font=("Segoe UI", 10)).pack(pady=(15, 5))
    entry_hotkey = tk.Entry(win, justify="center", font=("Segoe UI", 11))
    entry_hotkey.insert(0, current_cfg.get("hotkey", "f9"))
    entry_hotkey.pack()

    tk.Label(win, text="Позиция оверлея:", font=("Segoe UI", 10)).pack(pady=(10, 5))
    overlay_var = tk.StringVar(value=current_cfg.get("overlay_position", "bottom"))
    combo_overlay = ttk.Combobox(win, textvariable=overlay_var, values=["bottom", "top"], state="readonly", width=10)
    combo_overlay.pack()

    # Звук
    sound_var = tk.BooleanVar(value=current_cfg.get("sound_enabled", True))
    tk.Checkbutton(win, text="Включить звуковые сигналы", variable=sound_var, font=("Segoe UI", 10)).pack(pady=(15, 5))

    def save():
        new_cfg = current_cfg.copy()
        new_cfg["hotkey"] = entry_hotkey.get().strip().lower()
        new_cfg["overlay_position"] = overlay_var.get()
        new_cfg["sound_enabled"] = sound_var.get()

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, indent=2, ensure_ascii=False)
            
            on_save_callback(new_cfg)
            messagebox.showinfo("Успех", "Настройки сохранены!\n(Если вы меняли клавишу, перезапустите приложение).", parent=win)
            win.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}", parent=win)

    tk.Button(win, text="Сохранить", command=save, font=("Segoe UI", 11, "bold"), bg="#4CAF50", fg="white", width=15).pack(pady=20)