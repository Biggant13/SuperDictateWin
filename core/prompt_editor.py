import tkinter as tk
from tkinter import messagebox

def open_prompt_window(root, current_prompt, on_save_callback):
    win = tk.Toplevel(root)
    win.title("Промт для встреч")
    
    window_width = 500
    window_height = 400
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = screen_width - window_width - 40
    y = screen_height - window_height - 80
    win.geometry(f"{window_width}x{window_height}+{x}+{y}")
    win.attributes("-topmost", True)
    
    bg_color = "#1e1e1e"
    fg_color = "#ffffff"
    win.configure(bg=bg_color)

    lbl = tk.Label(win, text="Этот текст будет добавлен в начало каждого файла встречи.\nСкопируйте файл и отправьте нейросети для создания саммари:", 
                   bg=bg_color, fg=fg_color, font=("Segoe UI", 10), justify="left")
    lbl.pack(pady=10, padx=10, anchor="w")

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
        padx=10, pady=10
    )
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    # Вставляем текущий промт
    text_widget.insert(tk.END, current_prompt)

    def save():
        new_prompt = text_widget.get(1.0, tk.END).strip()
        on_save_callback(new_prompt)
        messagebox.showinfo("Сохранено", "Промт успешно обновлен!", parent=win)
        win.destroy()

    btn_save = tk.Button(
        win, 
        text="💾 Сохранить", 
        command=save, 
        bg="#4caf50", fg="white", 
        font=("Segoe UI", 10, "bold"), 
        relief="flat", cursor="hand2"
    )
    btn_save.pack(side=tk.BOTTOM, pady=10)