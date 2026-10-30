import json
import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd
from core.config import CONFIG_PATH

def open_settings_window(root, current_cfg, on_save_callback):
    """Открывает окно настроек поверх остальных."""
    win = tk.Toplevel(root)
    win.title("Настройки SuperDictate")
    win.geometry("350x460") # <-- Увеличили высоту окна
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

    # --- Микрофон ---
    tk.Label(win, text="Микрофон:", font=("Segoe UI", 10)).pack(pady=(10, 5))
    
    # Получаем список только входных устройств
    devices = sd.query_devices()
    input_devices = ["По умолчанию (системный)"]
    device_map = {"По умолчанию (системный)": ""}
    
    current_device_idx = current_cfg.get("input_device", "")
    current_device_name = "По умолчанию (системный)"
    
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            name = f"{dev['name']} ({i})"
            input_devices.append(name)
            device_map[name] = i
            if str(i) == str(current_device_idx):
                current_device_name = name

    device_var = tk.StringVar(value=current_device_name)
    combo_device = ttk.Combobox(win, textvariable=device_var, values=input_devices, state="readonly", width=40)
    combo_device.pack()

    # --- Позиция оверлея ---
    tk.Label(win, text="Позиция оверлея:", font=("Segoe UI", 10)).pack(pady=(10, 5))
    overlay_var = tk.StringVar(value=current_cfg.get("overlay_position", "bottom"))
    combo_overlay = ttk.Combobox(win, textvariable=overlay_var, values=["bottom", "top"], state="readonly", width=10)
    combo_overlay.pack()

    # --- Звук ---
    sound_var = tk.BooleanVar(value=current_cfg.get("sound_enabled", True))
    tk.Checkbutton(win, text="Включить звуковые сигналы", variable=sound_var, font=("Segoe UI", 10)).pack(pady=(15, 5))

    # --- Метод копирования ---
    tk.Label(win, text="Метод копирования контекста:", font=("Segoe UI", 10)).pack(pady=(10, 5))
    copy_method_var = tk.StringVar(value=current_cfg.get("copy_method", "insert"))
    combo_copy = ttk.Combobox(
        win,
        textvariable=copy_method_var,
        values=["insert", "ctrl_c"],
        state="readonly",
        width=15,
    )
    combo_copy.pack()
    tk.Label(
        win,
        text="insert = Ctrl+Insert (безопасно)\nctrl_c = Ctrl+C (может убить процесс в терминале)",
        font=("Segoe UI", 8),
        fg="#666666",
        justify="center",
    ).pack()

    def save():
        new_cfg = current_cfg.copy()
        new_cfg["hotkey"] = entry_hotkey.get().strip().lower()
        new_cfg["overlay_position"] = overlay_var.get()
        new_cfg["sound_enabled"] = sound_var.get()
        new_cfg["copy_method"] = copy_method_var.get()
        
        # Сохраняем индекс микрофона
        selected_dev_name = device_var.get()
        new_cfg["input_device"] = device_map.get(selected_dev_name, "")

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, indent=2, ensure_ascii=False)
            
            on_save_callback(new_cfg)
            messagebox.showinfo("Успех", "Настройки сохранены!\n(Если вы меняли клавишу, перезапустите приложение).", parent=win)
            win.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}", parent=win)

    tk.Button(win, text="Сохранить", command=save, font=("Segoe UI", 11, "bold"), bg="#4CAF50", fg="white", width=15).pack(pady=20)