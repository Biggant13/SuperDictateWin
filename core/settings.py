import json
import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd
from core.config import CONFIG_PATH
from core.autostart import is_enabled, set_enabled

def open_settings_window(root, current_cfg, on_save_callback):
    """Открывает окно настроек в тёмной теме с группировкой по блокам."""
    win = tk.Toplevel(root)
    win.title("Настройки SuperDictate")
    win.geometry("420x600")  # Оптимальная высота под новые блоки
    win.configure(bg="#202020")
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
    
    # Стили для блоков
    card_bg = "#282828"
    card_border = "#3a3a3a"

    # --- Класс для всплывающих подсказок ---
    class ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tipwindow = None
            self.id = None
            widget.bind("<Enter>", self.enter)
            widget.bind("<Leave>", self.leave)

        def enter(self, event=None):
            self.schedule()

        def leave(self, event=None):
            self.unschedule()
            self.hidetip()

        def schedule(self):
            self.unschedule()
            self.id = self.widget.after(500, self.showtip)

        def unschedule(self):
            id = self.id
            self.id = None
            if id:
                self.widget.after_cancel(id)

        def showtip(self, event=None):
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry("+%d+%d" % (x, y))
            tw.attributes("-topmost", True) # Чтобы подсказка была поверх окна
            label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                             background="#2d2d2d", foreground="#ffffff", relief="solid", borderwidth=1,
                             font=("Segoe UI", 9), padx=5, pady=5)
            label.pack(ipadx=1)

        def hidetip(self):
            tw = self.tipwindow
            self.tipwindow = None
            if tw:
                tw.destroy()

    # --- Функция создания блока (карточки) ---
    def create_card(title):
        frame = tk.Frame(win, bg=card_bg, highlightbackground=card_border, highlightthickness=1)
        frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        tk.Label(frame, text=title, bg=card_bg, fg="#ffffff", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(10, 5))
        return frame

    # ==========================================
    # БЛОК 1: Аудио и ввод
    # ==========================================
    card1 = create_card("🎤 Аудио и ввод")

    # Микрофон
    lbl_mic = tk.Label(card1, text="Микрофон:", bg=card_bg, fg=label_fg, font=label_font, anchor="w")
    lbl_mic.pack(fill=tk.X, padx=15, pady=(5, 2))
    ToolTip(lbl_mic, "Устройство, с которого записывается звук.\nЕсли не знаете, что выбрать — оставьте «По умолчанию».")
    
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
    combo_device = ttk.Combobox(card1, textvariable=device_var, values=input_devices, state="readonly")
    combo_device.pack(fill=tk.X, padx=15, pady=(0, 10), ipady=2)

    # Метод копирования
    lbl_copy = tk.Label(card1, text="Метод копирования контекста:", bg=card_bg, fg=label_fg, font=label_font, anchor="w")
    lbl_copy.pack(fill=tk.X, padx=15, pady=(5, 2))
    ToolTip(lbl_copy, "insert: Ctrl+Insert (безопасно, не завершает программы в консоли).\nctrl_c: Ctrl+C (классическое копирование, может убить процесс в терминале).")
    
    copy_method_var = tk.StringVar(value=current_cfg.get("copy_method", "insert"))
    combo_copy = ttk.Combobox(card1, textvariable=copy_method_var, values=["insert", "ctrl_c"], state="readonly")
    combo_copy.pack(fill=tk.X, padx=15, pady=(0, 15), ipady=2)

    # ==========================================
    # БЛОК 2: Интерфейс и система
    # ==========================================
    card2 = create_card("⚙️ Интерфейс и система")

    # Позиция оверлея
    lbl_overlay = tk.Label(card2, text="Позиция оверлея:", bg=card_bg, fg=label_fg, font=label_font, anchor="w")
    lbl_overlay.pack(fill=tk.X, padx=15, pady=(5, 2))
    ToolTip(lbl_overlay, "Где показывать плашку «Идёт запись...» — вверху или внизу экрана.")
    
    overlay_var = tk.StringVar(value=current_cfg.get("overlay_position", "bottom"))
    combo_overlay = ttk.Combobox(card2, textvariable=overlay_var, values=["bottom", "top"], state="readonly")
    combo_overlay.pack(fill=tk.X, padx=15, pady=(0, 10), ipady=2)

    # Чекбоксы
    check_style = {"bg": card_bg, "fg": "#ffffff", "selectcolor": entry_bg, 
                   "activebackground": card_bg, "activeforeground": "#ffffff", "font": label_font,
                   "highlightthickness": 0, "bd": 0}

    sound_var = tk.BooleanVar(value=current_cfg.get("sound_enabled", True))
    cb_sound = tk.Checkbutton(card2, text="Включить звуковые сигналы", variable=sound_var, **check_style)
    cb_sound.pack(anchor="w", padx=15, pady=(5, 0))
    ToolTip(cb_sound, "Короткие звуки (бипы), подтверждающие старт и стоп записи.")

    gpu_var = tk.BooleanVar(value=current_cfg.get("use_gpu", True))
    cb_gpu = tk.Checkbutton(card2, text="Использовать видеокарту (GPU)", variable=gpu_var, **check_style)
    cb_gpu.pack(anchor="w", padx=15, pady=(5, 0))
    ToolTip(cb_gpu, "Ускоряет распознавание через видеокарту. Требуется перезапуск.\nЕсли видеокарта не поддерживается, программа сама переключится на процессор.")

    autostart_var = tk.BooleanVar(value=is_enabled())
    cb_auto = tk.Checkbutton(card2, text="Запускать при старте Windows", variable=autostart_var, **check_style)
    cb_auto.pack(anchor="w", padx=15, pady=(5, 15))
    ToolTip(cb_auto, "Приложение будет тихо сворачиваться в трей при включении компьютера.")

    # ==========================================
    # Кнопка Сохранить
    # ==========================================
    def save():
        new_cfg = current_cfg.copy()
        new_cfg["overlay_position"] = overlay_var.get()
        new_cfg["sound_enabled"] = sound_var.get()
        new_cfg["use_gpu"] = gpu_var.get()
        new_cfg["copy_method"] = copy_method_var.get()
        
        selected_dev_name = device_var.get()
        new_cfg["input_device"] = device_map.get(selected_dev_name, "")

        # Если в конфиге не осталось координат (например, удалили), 
        # мы просто их не сохраняем, и оверлей вернется на место по умолчанию.
        if "overlay_x" in new_cfg and "overlay_y" in new_cfg:
            pass # Оставляем как есть

        try:
            old_gpu = current_cfg.get("use_gpu", True)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, indent=2, ensure_ascii=False)
            
            set_enabled(autostart_var.get())
            on_save_callback(new_cfg)
            
            gpu_changed = old_gpu != new_cfg["use_gpu"]
            
            msg = "Настройки сохранены!"
            if gpu_changed:
                msg += "\n\nВы изменили настройку видеокарты. Перезапустите приложение."
            
            messagebox.showinfo("Успех", msg, parent=win)
            win.destroy()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}", parent=win)

    btn_save = tk.Button(win, text="Сохранить", command=save, 
                         font=("Segoe UI", 11, "bold"), 
                         bg="#4CAF50", fg="white", 
                         activebackground="#45a049", activeforeground="white",
                         relief="flat", cursor="hand2")
    btn_save.pack(side=tk.BOTTOM, pady=25, ipadx=30, ipady=5)