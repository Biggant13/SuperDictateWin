import tkinter as tk

def open_help_window(root):
    win = tk.Toplevel(root)
    win.title("Как пользоваться")
    
    # Увеличили высоту до 480, чтобы всё влезло с запасом
    window_width = 460
    window_height = 480
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = screen_width - window_width - 40
    y = screen_height - window_height - 80
    win.geometry(f"{window_width}x{window_height}+{x}+{y}")
    win.attributes("-topmost", True)
    win.resizable(False, False)
    
    bg_color = "#1e1e1e"
    fg_color = "#ffffff"
    win.configure(bg=bg_color)

    # Заголовок
    tk.Label(win, text="SuperDictate", fg="#ffffff", bg=bg_color, font=("Segoe UI", 18, "bold")).pack(pady=(20, 5))
    tk.Label(win, text="Краткая инструкция", fg="#888888", bg=bg_color, font=("Segoe UI", 10)).pack(pady=(0, 15))

    # Функция для создания красивых блоков
    def add_section(hotkey, title, description, color):
        frame = tk.Frame(win, bg=bg_color)
        frame.pack(fill=tk.X, padx=40, pady=10)
        
        # Клавиша (слева)
        lbl_key = tk.Label(frame, text=hotkey, fg=color, bg=bg_color, font=("Segoe UI", 14, "bold"), width=4, anchor="w")
        lbl_key.pack(side=tk.LEFT, anchor="n")
        
        # Текст (справа)
        text_frame = tk.Frame(frame, bg=bg_color)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(text_frame, text=title, fg=fg_color, bg=bg_color, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(text_frame, text=description, fg="#aaaaaa", bg=bg_color, font=("Segoe UI", 9), justify="left", anchor="w", wraplength=320).pack(fill=tk.X)

    # Блоки
    add_section("F9", "Диктовка (Микрофон)", "Зажмите клавишу и говорите. Отпустите — текст распознается и вставится в активное окно.", "#4caf50")
    add_section("F8", "Диктовка (Системный звук)", "Зажмите клавишу и включите звук на компьютере. Отпустите — звук распознается и вставится текстом.", "#2196f3")
    add_section("F7", "Режим встреч (Нажмите 1 раз)", "Начинает запись встречи (микрофон + система). Нажмите F7 снова, чтобы остановить. Результат сохранится в 'Папку встреч' (в меню трея).", "#ff4d4d")
    
    # Подсказка про промт (теперь аккуратно прижата к низу)
    bottom_frame = tk.Frame(win, bg=bg_color)
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 20))
    
    tk.Label(bottom_frame, text="💡 Выберите Промт в меню трея перед встречей.\nОн добавится в начало файла для нейросети.", 
             fg="#ffa726", bg=bg_color, font=("Segoe UI", 9, "italic"), justify="center").pack()