import os
import tkinter as tk
from tkinter import ttk
from core.logger import LOG_FILE

MAX_LINES = 200
POLL_MS = 500

_instance = None


def open_log_viewer(root):
    """Открывает окно логов (синглтон — повторный вызов поднимает существующее)."""
    global _instance
    if _instance is not None and _instance.alive():
        _instance.focus()
        return
    _instance = LogViewerWindow(root)


class LogViewerWindow:
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.title("SuperDictate — Логи (live)")
        self.win.geometry("900x520")

        toolbar = tk.Frame(self.win)
        toolbar.pack(fill="x", padx=6, pady=6)

        self.auto_scroll = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="Авто-прокрутка", variable=self.auto_scroll).pack(side="left")

        self.autopoll = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="Live", variable=self.autopoll).pack(side="left", padx=(10, 0))

        tk.Button(toolbar, text="Обновить", command=self._reload).pack(side="right")
        tk.Button(toolbar, text="Очистить", command=self._clear).pack(side="right", padx=(0, 5))

        frame = tk.Frame(self.win)
        frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.text = tk.Text(
            frame, wrap="none", font=("Consolas", 9), state="disabled",
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
        )
        sb_y = ttk.Scrollbar(frame, command=self.text.yview)
        sb_x = ttk.Scrollbar(frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.text.tag_configure("ERROR", foreground="#f48771")
        self.text.tag_configure("WARNING", foreground="#dcdcaa")
        self.text.tag_configure("INFO", foreground="#d4d4d4")
        self.text.tag_configure("DEBUG", foreground="#808080")

        self._pos = 0
        self._poll_id = None
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._reload()
        self._schedule_poll()

    def alive(self):
        try:
            return self.win.winfo_exists()
        except Exception:
            return False

    def focus(self):
        try:
            self.win.deiconify()
            self.win.lift()
            self.win.focus_force()
        except Exception:
            pass

    def _tag_for(self, line):
        if " - ERROR - " in line:
            return "ERROR"
        if " - WARNING - " in line:
            return "WARNING"
        if " - DEBUG - " in line:
            return "DEBUG"
        return "INFO"

    def _append(self, line):
        self.text.configure(state="normal")
        self.text.insert("end", line, self._tag_for(line))

        total = int(self.text.index("end-1c").split(".")[0])
        if total > MAX_LINES:
            self.text.delete("1.0", f"{total - MAX_LINES + 1}.0")

        self.text.configure(state="disabled")

    def _reload(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-MAX_LINES:]
        except FileNotFoundError:
            lines = []
        except Exception as e:
            lines = [f"[LogViewer] Не удалось прочитать лог: {e}\n"]

        for line in lines:
            self._append(line)

        try:
            self._pos = os.path.getsize(LOG_FILE)
        except FileNotFoundError:
            self._pos = 0

        if self.auto_scroll.get():
            self.text.see("end")

    def _poll(self):
        if not self.autopoll.get():
            return
        try:
            size = os.path.getsize(LOG_FILE)
        except FileNotFoundError:
            return
        except Exception:
            return

        if size < self._pos:
            self._reload()
            return

        if size == self._pos:
            return

        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._pos)
                chunk = f.read()
                self._pos = f.tell()
        except Exception:
            return

        for line in chunk.splitlines(keepends=True):
            self._append(line)

        if self.auto_scroll.get():
            self.text.see("end")

    def _schedule_poll(self):
        self._poll()
        try:
            self._poll_id = self.win.after(POLL_MS, self._schedule_poll)
        except Exception:
            self._poll_id = None

    def _clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def _on_close(self):
        if self._poll_id:
            try:
                self.win.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
        try:
            self.win.destroy()
        except Exception:
            pass