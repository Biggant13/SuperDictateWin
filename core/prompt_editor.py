import tkinter as tk
from tkinter import messagebox, simpledialog

def open_prompt_window(root, prompts_dict, active_prompt_name, on_save_callback):
    win = tk.Toplevel(root)
    win.title("Менеджер промтов для встреч")
    
    # Высота увеличена до 530
    window_width = 700
    window_height = 530
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = screen_width - window_width - 40
    y = screen_height - window_height - 80
    win.geometry(f"{window_width}x{window_height}+{x}+{y}")
    win.attributes("-topmost", True)
    win.minsize(600, 450)
    
    bg_color = "#1e1e1e"
    fg_color = "#ffffff"
    win.configure(bg=bg_color)

    # --- Левая панель (Список промтов) ---
    left_frame = tk.Frame(win, bg=bg_color, width=220)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    left_frame.pack_propagate(False)

    tk.Label(left_frame, text="Сохраненные промты:", bg=bg_color, fg=fg_color, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))

    listbox = tk.Listbox(left_frame, bg="#2b2b2b", fg=fg_color, font=("Segoe UI", 10), relief="flat", highlightthickness=0)
    listbox.pack(fill=tk.BOTH, expand=True)

    # --- Правая панель (Редактор) ---
    right_frame = tk.Frame(win, bg=bg_color)
    right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

    tk.Label(right_frame, text="Текст промта (можно копировать Ctrl+C / Ctrl+V):", bg=bg_color, fg=fg_color, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))

    text_frame = tk.Frame(right_frame, bg=bg_color)
    text_frame.pack(fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text_widget = tk.Text(
        text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
        bg="#2b2b2b", fg=fg_color, font=("Segoe UI", 10),
        borderwidth=0, highlightthickness=0, padx=10, pady=10
    )
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    # --- Надежное копирование и вставка ---
    # 1. Контекстное меню по правому клику
    context_menu = tk.Menu(win, tearoff=0, bg="#2b2b2b", fg="white")
    context_menu.add_command(label="Копировать", command=lambda: text_widget.event_generate("<<Copy>>"))
    context_menu.add_command(label="Вставить", command=lambda: text_widget.event_generate("<<Paste>>"))
    
    def show_context_menu(event):
        context_menu.tk_popup(event.x_root, event.y_root)
    
    text_widget.bind("<Button-3>", show_context_menu)
    
    # 2. Явные горячие клавиши (обход багов Tkinter)
    def copy_text(event=None):
        try:
            sel = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            win.clipboard_clear()
            win.clipboard_append(sel)
        except tk.TclError:
            pass
        return "break"

    def paste_text(event=None):
        try:
            txt = win.clipboard_get()
            text_widget.insert(tk.INSERT, txt)
        except tk.TclError:
            pass
        return "break"

    text_widget.bind("<Control-c>", copy_text)
    text_widget.bind("<Control-v>", paste_text)
    text_widget.bind("<Control-C>", copy_text)
    text_widget.bind("<Control-V>", paste_text)

    # --- Логика работы с промтами ---
    current_selected_name = [None]
    active_name_ref = [active_prompt_name]

    def get_actual_name(display_name):
        return display_name.replace("✅", "").strip()

    def refresh_list():
        listbox.delete(0, tk.END)
        for i, name in enumerate(prompts_dict.keys()):
            if name == active_name_ref[0]:
                listbox.insert(tk.END, f"✅ {name}")
            else:
                listbox.insert(tk.END, f"   {name}")
            if name == current_selected_name[0]:
                listbox.selection_set(i)
                listbox.see(i)

    def on_select(event):
        selection = listbox.curselection()
        if selection:
            display_name = listbox.get(selection[0])
            name = get_actual_name(display_name)
            current_selected_name[0] = name
            active_name_ref[0] = name
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, prompts_dict.get(name, ""))
            
            # Сохраняем активный промт в конфиг сразу при клике
            on_save_callback(prompts_dict, active_name_ref[0])
            refresh_list()

    listbox.bind("<<ListboxSelect>>", on_select)

    def new_prompt():
        listbox.selection_clear(0, tk.END)
        current_selected_name[0] = None
        text_widget.delete(1.0, tk.END)
        text_widget.focus_set()

    def delete_prompt():
        if not current_selected_name[0]:
            messagebox.showwarning("Внимание", "Выберите промт из списка для удаления.", parent=win)
            return
        if messagebox.askyesno("Удаление", f"Удалить промт '{current_selected_name[0]}'?", parent=win):
            del prompts_dict[current_selected_name[0]]
            
            # Если удалили активный, делаем активным первый из оставшихся
            if active_name_ref[0] == current_selected_name[0]:
                active_name_ref[0] = list(prompts_dict.keys())[0] if prompts_dict else ""
            
            current_selected_name[0] = active_name_ref[0]
            on_save_callback(prompts_dict, active_name_ref[0])
            refresh_list()

    def save_prompt():
        text = text_widget.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Внимание", "Текст промта не может быть пустым.", parent=win)
            return

        name = current_selected_name[0]
        if name:
            prompts_dict[name] = text
            active_name_ref[0] = name
            on_save_callback(prompts_dict, active_name_ref[0])
            refresh_list()
            messagebox.showinfo("Сохранено", f"Промт '{name}' обновлен и выбран!", parent=win)
        else:
            new_name = simpledialog.askstring("Новый промт", "Введите название для этого промта:", parent=win)
            if new_name:
                new_name = new_name.strip()
                if new_name in prompts_dict:
                    messagebox.showerror("Ошибка", "Промт с таким названием уже существует.", parent=win)
                    return
                prompts_dict[new_name] = text
                active_name_ref[0] = new_name
                current_selected_name[0] = new_name
                on_save_callback(prompts_dict, active_name_ref[0])
                refresh_list()
                messagebox.showinfo("Сохранено", f"Создан новый промт '{new_name}'!", parent=win)

    # Инициализация UI
    refresh_list()
    text_widget.insert(tk.END, prompts_dict.get(active_name_ref[0], ""))
    
    # Кнопки
    btn_frame = tk.Frame(left_frame, bg=bg_color)
    btn_frame.pack(fill=tk.X, pady=(10, 0))

    btn_new = tk.Button(btn_frame, text="➕ Новый", command=new_prompt, bg="#2196f3", fg="white", relief="flat", cursor="hand2")
    btn_new.pack(fill=tk.X, pady=2)
    
    btn_del = tk.Button(btn_frame, text="🗑 Удалить", command=delete_prompt, bg="#f44336", fg="white", relief="flat", cursor="hand2")
    btn_del.pack(fill=tk.X, pady=2)

    btn_save = tk.Button(right_frame, text="💾 Сохранить и использовать для встреч", command=save_prompt, bg="#4caf50", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2")
    btn_save.pack(fill=tk.X, pady=(10, 0))