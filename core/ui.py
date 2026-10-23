import ctypes
import tkinter as tk

class RecordingOverlay:
    # Добавили is_processing_cb
    def __init__(self, is_recording_cb, is_processing_cb, position="bottom"):
        self.is_recording_cb = is_recording_cb
        self.is_processing_cb = is_processing_cb
        
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="#202020")
        self.root.attributes("-toolwindow", True)

        w, h = 220, 46  # Чуть шире, чтобы влез длинный текст
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = 60 if position == "top" else sh - h - 80
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(self.root, bg="#202020", highlightthickness=1, highlightbackground="#555555")
        frame.pack(fill="both", expand=True)
        
        # Сохраняем ссылку на label, чтобы менять текст
        self.label = tk.Label(frame, text="", fg="#ffffff", bg="#202020",
                              font=("Segoe UI", 11, "bold"))
        self.label.pack(expand=True, fill="both")

        self.root.update_idletasks()
        GWL_EXSTYLE, WS_EX_NOACTIVATE = -20, 0x08000000
        WS_EX_TOOLWINDOW, WS_EX_TOPMOST = 0x00000080, 0x00000008
        u = ctypes.windll.user32
        hwnd = u.GetAncestor(self.root.winfo_id(), 2)
        if hwnd:
            ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)

        self.root.withdraw()
        self._visible = False
        self._poll()

    def _poll(self):
        is_rec = self.is_recording_cb()
        is_proc = self.is_processing_cb()
        
        # Окно показывается, если идет запись ИЛИ идет обработка
        active = is_rec or is_proc

        if active and not self._visible:
            self.root.deiconify()
            self._visible = True
        elif not active and self._visible:
            self.root.withdraw()
            self._visible = False

        # Меняем текст в зависимости от состояния
        if is_rec:
            text = "🔴  Идёт запись..."
        elif is_proc:
            text = "⏳  Перевожу в текст..."
        else:
            text = ""

        if self.label.cget("text") != text:
            self.label.config(text=text)

        self.root.after(50, self._poll)

    def run(self):
        self.root.mainloop()
        
    def quit(self):
        self.root.quit()