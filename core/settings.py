import json
import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd
from core.config import CONFIG_PATH

def open_settings_window(root, current_cfg, on_save_callback):
    """Открывает окно настроек в тёмной теме."""
    win = tk.Toplevel(root)
    win.title("Настройки SuperDictate")
    win.geometry("380x680")  # Увеличили высоту, чтобы всё влезло
    win.configure(bg="#202020")  # Тёмный фон окна
    win.attributes("-topmost", True)
    win.resizable(False, False)

    # Центрируем окно
    win.update_idletasks()
    x = (win.winfo_screenwidth() - win.winfo_width()) // 2
    y = (win.winfo_screenheight() - win.winfo_height()) // 2
    win.geometry(f"+{x}+{y}")

    # --- Стилизация ttk (для Combobox) ---
    style = ttk.Style(win)
    style.theme_use('clam')
    style.configure("TCombobox", 
                    fieldbackground="#2d2d2d", background="#202020", 
                    foreground="#ffffff", arrowcolor="#ffffff", 
                    bordercolor="#555555", lightcolor="#555555", darkcolor="#555555")
    style.map("TCombobox", fieldbackground=[("readonly", "#2d2d2d")], foreground=[("readonly", "#ffffff")])

    # --- Общие стили ---
    label_font = ("Segoe UI", 10)
    label_fg = "#cccccc"
    entry_bg = "#2d2d2d"
    entry_fg = "#ffffff"
    entry_hl = "#555555"

    def create_label(text, pady=(15, 5), fg=label_fg, font=label_font):
        tk.Label(win, text=text, bg="#202020", fg=fg, font=font).pack(pady=pady)

    # --- Горячая клавиша ---
    create_label("Горячая клавиша (напр. f9):", pady=(15, 5))
    entry_hotkey = tk.Entry(win, justify="center", font=("Segoe UI", 11), 
                            bg=entry_bg, fg=entry_fg, insertbackground=entry_fg,
                            relief="flat", highlightthickness=1, highlightbackground=entry_hl, highlightcolor="#4CAF50")
    entry_hotkey.insert(0, current_cfg.get("hotkey", "f9"))
    entry_hotkey.pack(ipady=4, padx=20, fill="x")

    # --- Микрофон ---
    create_label("Микрофон:", pady=(15, 5))
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
    combo_device.pack(ipady=2)

    # --- Позиция оверлея ---
    create_label("Позиция оверлея:", pady=(15, 5))
    overlay_var = tk.StringVar(value=current_cfg.get("overlay_position", "bottom"))
    combo_overlay = ttk.Combobox(win, textvariable=overlay_var, values=["bottom", "top"], state="readonly", width=15)
    combo_overlay.pack(ipady=2)

    # --- Звук ---
    check_style = {"bg": "#202020", "fg": "#ffffff", "selectcolor": entry_bg, 
                   "activebackground": "#202020", "activeforeground": "#ffffff", "font": label_font}

    sound_var = tk.BooleanVar(value=current_cfg.get("sound_enabled", True))
    tk.Checkbutton(win, text="Включить звуковые сигналы", variable=sound_var, **check_style).pack(pady=(15, 5))

    # --- GPU (Видеокарта) ---
    gpu_var = tk.BooleanVar(value=current_cfg.get("use_gpu", True))
    tk.Checkbutton(win, text="Использовать видеокарту (GPU)", variable=gpu_var, **check_style).pack(pady=5)

    # --- Метод копирования ---
    create_label("Метод копирования контекста:", pady=(15, 5))
    copy_method_var = tk.StringVar(value=current_cfg.get("copy_method", "insert"))
    combo_copy = ttk.Combobox(
        win,
        textvariable=copy_method_var,
        values=["insert", "ctrl_c"],
        state="readonly",
        width=15,
    )
    combo_copy.pack(ipady=2)
    tk.Label(
        win,
        text="insert = Ctrl+Insert (безопасно)\nctrl_c = Ctrl+C (может убить процесс в терминале)",
        font=("Segoe UI", 8),
        fg="#888888", # Сделали цвет светлее, чтобы читалось на тёмном фоне
        bg="#202020",
        justify="center",
    ).pack(pady=(5, 0))

    def save():
        new_cfg = current_cfg.copy()
        new_cfg["hotkey"] = entry_hotkey.get().strip().lower()
        new_cfg["overlay_position"] = overlay_var.get()
        new_cfg["sound_enabled"] = sound_var.get()
        new_cfg["use_gpu"] = gpu_var.get()
        new_cfg["copy_method"] = copy_method_var.get()
        
        selected_dev_name = device_var.get()
        new_cfg["input_device"] = device_map.get(selected_dev_name, "")

        # 1) Валидация хоткея
        try:
            from core.utils import parse_hotkey
            parse_hotkey(new_cfg["hotkey"])
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректная комбинация: {e}", parent=win)
            return

        try:
            old_hotkey = current_cfg.get("hotkey", "")
            old_gpu = current_cfg.get("use_gpu", True)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, indent=2, ensure_ascii=False)
            
            on_save_callback(new_cfg)
            
            hotkey_changed = old_hotkey != new_cfg["hotkey"]
            gpu_changed = old_gpu != new_cfg["use_gpu"]
            
            msg = "Настройки сохранены!"
            if hotkey_changed and gpu_changed:
                msg += "\n\nВы изменили хоткей и видеокарту. Перезапустите приложение."
            elif hotkey_changed:
                msg += "\n\nВы изменили горячую клавишу. Перезапустите приложение."
            elif gpu_changed:
                msg += "\n\nВы изменили настройку видеокарты. Перезапустите приложение."
            
            messagebox.showinfo("Успех", msg, parent=win)
            win.destroy()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}", parent=win)

    # --- Кнопка Сохранить ---
    btn_save = tk.Button(win, text="Сохранить", command=save, 
                         font=("Segoe UI", 11, "bold"), 
                         bg="#4CAF50", fg="white", 
                         activebackground="#45a049", activeforeground="white",
                         relief="flat", cursor="hand2")
    btn_save.pack(pady=25, ipadx=20, ipady=5)