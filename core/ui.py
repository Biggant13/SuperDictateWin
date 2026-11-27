from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath

class RecordingOverlay(QWidget):
    WIDTH = 250
    HEIGHT = 56
    PADDING = 10
    NUM_SEGMENTS = 16
    SEGMENT_GAP = 2

    COLOR_BG        = QColor("#1e1e1e")
    COLOR_DOT_REC   = QColor("#ff4444")
    COLOR_DOT_PROC  = QColor("#ffaa00")
    COLOR_TEXT      = QColor("#ffffff")
    COLOR_TEXT_DIM  = QColor("#888888")
    COLOR_BAR_BG    = QColor("#2b2b2b")
    COLOR_SEG_LOW   = QColor("#4caf50")
    COLOR_SEG_MID   = QColor("#ffc107")
    COLOR_SEG_HIGH  = QColor("#f44336")

    def __init__(self, is_recording_cb, is_processing_cb, position,
                 level_cb=None, elapsed_cb=None, source_cb=None, 
                 initial_x=None, initial_y=None, on_pos_change_cb=None):
        super().__init__()
        self.is_recording_cb = is_recording_cb
        self.is_processing_cb = is_processing_cb
        self.level_cb = level_cb
        self.elapsed_cb = elapsed_cb
        self.source_cb = source_cb
        self.on_pos_change_cb = on_pos_change_cb

        # Добавляем WindowDoesNotAcceptFocus и WA_ShowWithoutActivating
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._bg_alpha = 220 # Прозрачность (0-255)
        self._active_count = -1
        self._last_timer_str = ""
        self._is_dragging = False
        self._drag_pos = QPoint()

        # Позиционирование
        self._update_position(initial_x, initial_y)
        
        # Таймер обновления (аналог root.after)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(50)

        self.hide() # Изначально скрыто

    def _update_position(self, x, y):
        screen = QApplication.primaryScreen().geometry()
        if x is not None and y is not None:
            if x < 0 or x > screen.width() - 50 or y < 0 or y > screen.height() - 50:
                x = (screen.width() - self.WIDTH) // 2
                y = screen.height() - self.HEIGHT - 80
        else:
            x = (screen.width() - self.WIDTH) // 2
            y = screen.height() - self.HEIGHT - 80
        self.move(int(x), int(y))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Фон с закруглением
        painter.setBrush(self.COLOR_BG)
        painter.setPen(Qt.NoPen)
        painter.setOpacity(self._bg_alpha / 255.0)
        painter.drawRoundedRect(0, 0, self.WIDTH, self.HEIGHT, 8, 8)
        painter.setOpacity(1.0)

        # 2. Точка статуса и Текст
        is_proc = self.is_processing_cb()
        is_rec = self.is_recording_cb()
        
        dot_color = self.COLOR_DOT_PROC if is_proc else self.COLOR_DOT_REC
        painter.setBrush(dot_color)
        painter.drawEllipse(self.PADDING, 8, 12, 12)

        text = "Перевожу в текст" if is_proc else "REC"
        if is_rec and self.source_cb:
            src = self.source_cb()
            if src == "micro": text = "REC Micro"
            elif src == "system": text = "REC System"

        painter.setPen(self.COLOR_TEXT)
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(self.PADDING + 18, 18, text)

        # 3. Таймер
        elapsed = 0.0
        if self.elapsed_cb:
            try: elapsed = float(self.elapsed_cb() or 0.0)
            except: pass
        total = max(0, int(elapsed))
        timer_str = f"{total // 60}:{total % 60:02d}"
        
        painter.setFont(QFont("Consolas", 11, QFont.Bold))
        fm = painter.fontMetrics()
        painter.drawText(self.WIDTH - self.PADDING - fm.horizontalAdvance(timer_str), 18, timer_str)

        # 4. VU-метр
        bar_left = self.PADDING
        bar_right = self.WIDTH - self.PADDING
        total_w = bar_right - bar_left
        seg_w = (total_w - (self.NUM_SEGMENTS - 1) * self.SEGMENT_GAP) / self.NUM_SEGMENTS

        level = 0.0
        if is_rec and self.level_cb:
            try: level = max(0.0, min(1.0, float(self.level_cb() or 0.0)))
            except: pass
        active_segs = int(round(level * self.NUM_SEGMENTS)) if is_rec else 0

        painter.setPen(Qt.NoPen)
        for i in range(self.NUM_SEGMENTS):
            x0 = bar_left + i * (seg_w + self.SEGMENT_GAP)
            ratio = i / (self.NUM_SEGMENTS - 1)
            
            if i < active_segs:
                color = self.COLOR_SEG_LOW if ratio < 0.6 else (self.COLOR_SEG_MID if ratio < 0.85 else self.COLOR_SEG_HIGH)
            else:
                color = self.COLOR_BAR_BG
                
            painter.setBrush(color)
            painter.drawRect(int(x0), 30, int(seg_w), 14)

    def _poll(self):
        try:
            processing = self.is_processing_cb()
            recording = self.is_recording_cb()

            if processing or recording:
                if not self.isVisible():
                    self.show()
                    self.raise_()
            else:
                if self.isVisible():
                    self.hide()

            if self.isVisible():
                self.update() # Перерисовать
        except Exception:
            pass

    # --- Обработчики мыши для перетаскивания ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            if self.on_pos_change_cb:
                self.on_pos_change_cb(self.x(), self.y())
            event.accept()