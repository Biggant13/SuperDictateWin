import tkinter as tk
import time
import math
import threading
from core.version import __version__

class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True) 
        self.root.attributes("-topmost", True) 
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#202020")

        w, h = 320, 200
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(self.root, bg="#202020", highlightthickness=1, highlightbackground="#555555")
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="SuperDictate", fg="#ffffff", bg="#202020", 
                 font=("Segoe UI", 18, "bold")).pack(pady=(15, 0))
        tk.Label(frame, text=f"v{__version__}", fg="#888888", bg="#202020", 
                 font=("Segoe UI", 10)).pack()

        self.canvas = tk.Canvas(frame, width=160, height=90, bg="#202020", highlightthickness=0)
        self.canvas.pack(pady=(5, 0))
        
        self.center_x, self.center_y = 80, 45
        self.rings = []
        self.frame_count = 0
        self._after_id = None
        self.start_time = time.time() 
        
        self.canvas.create_oval(self.center_x-8, self.center_y-8, self.center_x+8, self.center_y+8, 
                                fill="#ff4d4d", outline="", tags="core_dot")

        self.status_var = tk.StringVar(value="Инициализация...")
        tk.Label(frame, textvariable=self.status_var, fg="#cccccc", bg="#202020", 
                 font=("Segoe UI", 10), wraplength=280, justify="center").pack(pady=(5, 0))
                 
        # Запускаем анимацию безопасно через after
        self._after_id = self.root.after(100, self._animate)
        self.root.update_idletasks()

    def _animate(self):
        if not self.root.winfo_exists():
            return

        self.frame_count += 1
        
        core_r = 8 + math.sin(self.frame_count * 0.15) * 2
        self.canvas.coords("core_dot", 
            self.center_x - core_r, self.center_y - core_r,
            self.center_x + core_r, self.center_y + core_r)

        if self.frame_count == 1 or self.frame_count % 6 == 0:
            ring_id = self.canvas.create_oval(
                self.center_x - 8, self.center_y - 8,
                self.center_x + 8, self.center_y + 8,
                outline="#ff4d4d", width=3
            )
            self.rings.append({"id": ring_id, "r": 8, "alpha": 1.0})

        for ring in self.rings[:]:
            ring["r"] += 1.5
            ring["alpha"] = 1.0 - (ring["r"] / 45.0)

            if ring["r"] >= 45:
                self.canvas.delete(ring["id"])
                self.rings.remove(ring)
                continue

            t = max(0.0, ring["alpha"])
            r_col = int(32 + (255 - 32) * t)
            g_col = int(32 + (77 - 32) * t)
            b_col = int(32 + (77 - 32) * t)
            color = f"#{r_col:02x}{g_col:02x}{b_col:02x}"

            self.canvas.coords(
                ring["id"],
                self.center_x - ring["r"], self.center_y - ring["r"],
                self.center_x + ring["r"], self.center_y + ring["r"]
            )
            self.canvas.itemconfig(ring["id"], outline=color)

        self._after_id = self.root.after(30, self._animate)

    def set_status(self, text: str):
        try:
            self.root.after(0, lambda: self.status_var.set(text))
        except Exception:
            pass

    def run(self):
        self.root.mainloop()

    def close(self):
        try:
            if threading.current_thread() is not threading.main_thread():
                self.root.after(0, self.close)
                return

            elapsed = time.time() - getattr(self, "start_time", time.time())
            if elapsed < 1.5:
                delay_ms = int((1.5 - elapsed) * 1000)
                self.root.after(delay_ms, self._close_immediately)
            else:
                self._close_immediately()
        except Exception:
            pass

    def _close_immediately(self):
        try:
            if getattr(self, "_after_id", None) is not None:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass