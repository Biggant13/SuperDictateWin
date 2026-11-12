import tkinter as tk
from core.version import __version__

class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True) # Убираем рамки окна
        self.root.attributes("-topmost", True) # Поверх всех окон
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#202020")

        # Размеры и центрирование (увеличили высоту со 140 до 170)
        w, h = 320, 170
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(self.root, bg="#202020", highlightthickness=1, highlightbackground="#555555")
        frame.pack(fill="both", expand=True)

        # Название и версия
        tk.Label(frame, text="SuperDictate", fg="#ffffff", bg="#202020", 
                 font=("Segoe UI", 18, "bold")).pack(pady=(15, 0))
        tk.Label(frame, text=f"v{__version__}", fg="#888888", bg="#202020", 
                 font=("Segoe UI", 10)).pack()

        # Статус загрузки (добавили wraplength=280 и justify="center")
        self.status_var = tk.StringVar(value="Инициализация...")
        tk.Label(frame, textvariable=self.status_var, fg="#cccccc", bg="#202020", 
                 font=("Segoe UI", 10), wraplength=280, justify="center").pack(pady=(15, 0))

    def set_status(self, text: str):
        self.status_var.set(text)

    def run(self):
        self.root.mainloop()

    def close(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass