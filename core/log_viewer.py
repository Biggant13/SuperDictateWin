import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont, QCursor

from core.config import BASE_DIR
from core.qt_utils import get_qapp

# Имя файла лога (если у тебя в logger.py другое имя, поменяй здесь)
LOG_FILE = os.path.join(BASE_DIR, "superdictate.log")

_instance = None

class LogViewerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Просмотр логов")
        self.resize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QPushButton { 
                background-color: #333333; color: white; border: 1px solid #555; 
                border-radius: 4px; padding: 6px 12px; font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #444444; }
        """)

        self._file_pos = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Текстовое поле для логов
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #111111;
                color: #f8f8f2;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.text_edit)

        # Кнопки внизу
        btn_layout = QHBoxLayout()
        
        self.btn_clear = QPushButton("🗑 Очистить вид")
        self.btn_clear.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_clear.clicked.connect(self.text_edit.clear)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

        # Таймер для чтения новых строк
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(1000) # Раз в секунду

        # Первичная загрузка
        self._load_initial()

    def _load_initial(self):
        """Загружает последние 1000 строк при открытии."""
        if not os.path.exists(LOG_FILE):
            return
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Берем только последние 1000 строк, чтобы не вешать окно
                for line in lines[-1000:]:
                    self._append_line(line)
                self._file_pos = f.tell()
        except Exception as e:
            self._append_line(f"[Ошибка чтения лога: {e}]\n")

    def _append_line(self, line):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Настройка цвета в зависимости от содержания
        fmt = QTextCharFormat()
        if "ERROR" in line or "CRITICAL" in line or "Exception" in line or "Ошибка" in line:
            fmt.setForeground(QColor("#ff5555")) # Красный
        elif "WARNING" in line or "WARN" in line:
            fmt.setForeground(QColor("#f1fa8c")) # Желтый
        elif "INFO" in line:
            fmt.setForeground(QColor("#50fa7b")) # Зеленый
        elif "DEBUG" in line:
            fmt.setForeground(QColor("#6272a4")) # Серо-синий
        else:
            fmt.setForeground(QColor("#f8f8f2")) # Белый (по умолчанию)

        cursor.insertText(line, fmt)
        self.text_edit.setTextCursor(cursor)
        
        # Автоскролл вниз, только если пользователь не отлистал вверх
        sb = self.text_edit.verticalScrollBar()
        if sb.value() >= sb.maximum() - 50:
            sb.setValue(sb.maximum())

    def _poll(self):
        if not os.path.exists(LOG_FILE):
            return
            
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                f.seek(self._file_pos)
                new_lines = f.readlines()
                self._file_pos = f.tell()
                
            for line in new_lines:
                self._append_line(line)
                
        except Exception:
            pass

def open_log_viewer(root=None):
    """Открывает окно логов (синглтон)."""
    global _instance
    app = get_qapp()
    
    if _instance is not None and _instance.isVisible():
        _instance.raise_()
        _instance.activateWindow()
        return
        
    _instance = LogViewerDialog()
    _instance.show()