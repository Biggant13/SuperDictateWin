import tkinter as tk
import time


class RecordingOverlay:
    # Размеры окна (немного шире для русского текста)
    WIDTH = 250
    HEIGHT = 56
    PADDING = 10
    NUM_SEGMENTS = 16
    SEGMENT_GAP = 2

    # Цвета
    COLOR_BG        = "#1e1e1e"
    COLOR_DOT_REC   = "#ff4444"
    COLOR_DOT_PROC  = "#ffaa00"
    COLOR_TEXT      = "#ffffff"
    COLOR_TEXT_DIM  = "#888888"
    COLOR_BAR_BG    = "#2b2b2b"
    COLOR_SEG_LOW   = "#4caf50"
    COLOR_SEG_MID   = "#ffc107"
    COLOR_SEG_HIGH  = "#f44336"

    def __init__(self, is_recording_cb, is_processing_cb, position,
                 level_cb=None, elapsed_cb=None):
        self.is_recording_cb = is_recording_cb
        self.is_processing_cb = is_processing_cb
        self.level_cb = level_cb
        self.elapsed_cb = elapsed_cb

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Изначально скрываем окно
        self.root.withdraw() 
        self._visible = False
        self._bg_alpha = 0.85

        self.root.configure(bg=self.COLOR_BG)

        self.canvas = tk.Canvas(
            self.root, width=self.WIDTH, height=self.HEIGHT,
            bg=self.COLOR_BG, highlightthickness=0
        )
        self.canvas.pack()

        # 1. Точка статуса
        self.dot = self.canvas.create_oval(
            self.PADDING, 8, self.PADDING + 12, 20,
            fill=self.COLOR_DOT_REC, outline=""
        )
        # 2. Текст статуса
        self.status_text = self.canvas.create_text(
            self.PADDING + 18, 14, text="REC", anchor="w",
            fill=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")
        )
        # 3. Таймер
        self.timer_text = self.canvas.create_text(
            self.WIDTH - self.PADDING, 14, text="0:00", anchor="e",
            fill=self.COLOR_TEXT, font=("Consolas", 11, "bold")
        )

        # 4. Сегменты VU-метра
        bar_left  = self.PADDING
        bar_right = self.WIDTH - self.PADDING
        total_w   = bar_right - bar_left
        seg_w     = (total_w - (self.NUM_SEGMENTS - 1) * self.SEGMENT_GAP) / self.NUM_SEGMENTS
        self.segments = []
        for i in range(self.NUM_SEGMENTS):
            x0 = bar_left + i * (seg_w + self.SEGMENT_GAP)
            x1 = x0 + seg_w
            ratio = i / (self.NUM_SEGMENTS - 1)
            color = (self.COLOR_SEG_LOW if ratio < 0.6
                     else self.COLOR_SEG_MID if ratio < 0.85
                     else self.COLOR_SEG_HIGH)
            seg = self.canvas.create_rectangle(
                x0, 30, x1, 44, fill=self.COLOR_BAR_BG, outline=""
            )
            self.segments.append((seg, color))

        self._active_count = -1
        self._last_timer_str = ""

        # ПРИНУДИТЕЛЬНО ставим внизу по центру, игнорируя старые координаты из конфига
        self.update_position() 
        self._poll()

    def update_position(self):
        """Вычисляет позицию внизу по центру экрана"""
        try:
            self.root.update_idletasks() 
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            
            x = (screen_w - self.WIDTH) // 2
            y = screen_h - self.HEIGHT - 80  # 80px отступ от нижнего края
            
            self.root.geometry(f"+{int(x)}+{int(y)}")
        except Exception:
            # Фоллбэк на всякий случай
            self.root.geometry("+100+100")

    def _set_active_segments(self, count):
        if count == self._active_count:
            return
        for i, (seg, color) in enumerate(self.segments):
            self.canvas.itemconfig(
                seg, fill=color if i < count else self.COLOR_BAR_BG
            )
        self._active_count = count

    def _set_timer(self, elapsed):
        total = max(0, int(elapsed))
        text = f"{total // 60}:{total % 60:02d}"
        if text != self._last_timer_str:
            self.canvas.itemconfig(self.timer_text, text=text)
            self._last_timer_str = text

    def _poll(self):
        try:
            processing = self.is_processing_cb()
            recording  = self.is_recording_cb()

            # --- ЛОГИКА СКРЫТИЯ/ПОКАЗА ---
            if processing or recording:
                if not self._visible:
                    self.root.deiconify()
                    self.root.attributes("-alpha", self._bg_alpha)
                    self._visible = True
            else:
                if self._visible:
                    self.root.withdraw()
                    self._visible = False

            # --- ОТРИСОВКА ---
            if self._visible:
                if processing:
                    self.canvas.itemconfig(self.dot, fill=self.COLOR_DOT_PROC)
                    # Изменили текст на русский
                    self.canvas.itemconfig(self.status_text, text="Перевожу в текст")
                    self._set_active_segments(0)
                    if self.elapsed_cb:
                        try:
                            self._set_timer(float(self.elapsed_cb() or 0.0))
                        except Exception:
                            pass

                elif recording:
                    self.canvas.itemconfig(self.dot, fill=self.COLOR_DOT_REC)
                    self.canvas.itemconfig(self.status_text, text="REC")
                    
                    if self.level_cb:
                        try:
                            lvl = max(0.0, min(1.0, float(self.level_cb() or 0.0)))
                        except Exception:
                            lvl = 0.0
                        self._set_active_segments(int(round(lvl * self.NUM_SEGMENTS)))
                    
                    if self.elapsed_cb:
                        try:
                            self._set_timer(float(self.elapsed_cb() or 0.0))
                        except Exception:
                            pass

        except Exception:
            pass

        self.root.after(50, self._poll)

    def run(self):
        self.root.mainloop()

    def quit(self):
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass