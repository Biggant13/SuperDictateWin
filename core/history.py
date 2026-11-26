import os
import json
import pyperclip
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QScrollArea, QWidget, QFrame, QMessageBox, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from core.config import BASE_DIR
from core.qt_utils import get_qapp

HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
MAX_RECORDS = 100

# --- ЛОГИКА РАБОТЫ С ФАЙЛОМ ---
def _save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[History] Ошибка сохранения: {e}")

def _migrate_entry(item):
    if isinstance(item, str):
        return {"text": item, "favorite": False}
    if isinstance(item, dict) and "text" in item:
        return {
            "text": str(item.get("text", "")),
            "favorite": bool(item.get("favorite", False)),
        }
    return None

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            normalized = _migrate_entry(item)
            if normalized is not None:
                result.append(normalized)
        return result
    except Exception:
        return []

def add_record(text):
    if not text or not text.strip():
        return
    history = load_history()
    history.insert(0, {"text": text.strip(), "favorite": False})
    history = history[:MAX_RECORDS]
    _save_history(history)

def clear_history():
    history = load_history()
    favorites = [h for h in history if h.get("favorite", False)]
    _save_history(favorites)


# --- ВИЗУАЛЬНАЯ ЧАСТЬ (PySide6) ---

class RecordCard(QFrame):
    """Карточка одной записи."""
    def __init__(self, parent_dialog, index, record_data):
        super().__init__()
        self.parent_dialog = parent_dialog
        self.index = index
        self.record_data = record_data
        self.is_fav = record_data.get("favorite", False)
        
        self.setObjectName("RecordCard")

        # Настройка карточки (без лишних отступов внутри)
        self.setStyleSheet(f"""
            QFrame#RecordCard {{
                background-color: {"#3a3a2a" if self.is_fav else "#2d2d2d"};
                border: 1px solid {"#ffc107" if self.is_fav else "#444"};
                border-radius: 6px;
            }}
            QFrame#RecordCard:hover {{
                border: 1px solid {"#ffca28" if self.is_fav else "#777"};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6) # Компактные отступы
        layout.setSpacing(8)

        # 1. Кнопка-звезда (используем строгие символы)
        self.btn_star = QPushButton("★" if self.is_fav else "☆")
        self.btn_star.setFixedSize(25, 25)
        self.btn_star.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_star.setStyleSheet(f"background: transparent; border: none; font-size: 18px; color: {'#ffc107' if self.is_fav else '#888'};")
        self.btn_star.clicked.connect(self.parent_dialog.toggle_favorite)
        layout.addWidget(self.btn_star)

        # 2. Текст (клик копирует)
        self.lbl_text = QLabel(record_data.get("text", ""))
        self.lbl_text.setWordWrap(True)
        # background: transparent — убирает те самые прямоугольники!
        self.lbl_text.setStyleSheet(f"background: transparent; color: {'#fff59d' if self.is_fav else '#ffffff'}; font-family: 'Segoe UI'; font-size: 13px;")
        self.lbl_text.setCursor(QCursor(Qt.PointingHandCursor))
        self.lbl_text.mousePressEvent = self.copy_text
        layout.addWidget(self.lbl_text, stretch=1)

        # 3. Кнопка удаления (крестик вместо мусорки)
        self.btn_trash = QPushButton("✕")
        self.btn_trash.setFixedSize(25, 25)
        self.btn_trash.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_trash.setStyleSheet("background: transparent; border: none; font-size: 16px; color: #f44336; font-weight: bold;")
        self.btn_trash.clicked.connect(self.parent_dialog.delete_record)
        layout.addWidget(self.btn_trash)

    def copy_text(self, event):
        text = self.record_data.get("text", "")
        # Используем pyperclip вместо QApplication.clipboard() — обходит ошибку COM в Windows
        try:
            pyperclip.copy(text)
            self.lbl_text.setText("✅ Скопировано!")
            QApplication.processEvents()
            
            import threading
            import time
            def restore():
                time.sleep(1)
                self.lbl_text.setText(text)
            threading.Thread(target=restore, daemon=True).start()
        except Exception as e:
            print(f"Ошибка копирования: {e}")


class HistoryDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("История распознаваний")
        self.resize(550, 600)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QScrollArea { border: none; background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; }
        """)
        
        self.history = load_history()
        self.filter_favorites = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Шапка с фильтром ---
        header_layout = QHBoxLayout()
        self.btn_filter = QPushButton("★ Показать только избранные")
        self.btn_filter.setStyleSheet("""
            QPushButton {
                background-color: #e67e22; color: white; font-family: 'Segoe UI'; font-weight: bold;
                font-size: 13px; border-radius: 4px; padding: 6px 12px; border: 1px solid #d35400;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.btn_filter.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_filter.clicked.connect(self.toggle_filter)
        header_layout.addWidget(self.btn_filter)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Скролл с карточками ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(2) # Минимальный отступ между карточками
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # --- Подвал с очисткой ---
        self.btn_clear = QPushButton("🗑 Очистить историю (без избранных)")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; color: white; font-family: 'Segoe UI'; font-weight: bold;
                font-size: 13px; border-radius: 4px; padding: 8px; border: none;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_clear.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_clear.clicked.connect(self.clear_history_action)
        main_layout.addWidget(self.btn_clear)

        self.render_list()

    def render_list(self):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        visible_items = []
        for i, item in enumerate(self.history):
            if self.filter_favorites and not item.get("favorite", False):
                continue
            visible_items.append((i, item))

        if not visible_items:
            lbl_empty = QLabel("Нет записей для отображения")
            lbl_empty.setStyleSheet("color: #888; font-size: 14px; background: transparent;")
            lbl_empty.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(lbl_empty)
        else:
            for idx, item in visible_items:
                card = RecordCard(self, idx, item)
                self.scroll_layout.addWidget(card)

    def toggle_filter(self):
        self.filter_favorites = not self.filter_favorites
        if self.filter_favorites:
            self.btn_filter.setText("★ Показать все записи")
            self.btn_filter.setStyleSheet("""
                QPushButton {
                    background-color: #555; color: white; font-family: 'Segoe UI'; font-weight: bold;
                    font-size: 13px; border-radius: 4px; padding: 6px 12px; border: 1px solid #777;
                }
            """)
        else:
            self.btn_filter.setText("★ Показать только избранные")
            self.btn_filter.setStyleSheet("""
                QPushButton {
                    background-color: #e67e22; color: white; font-family: 'Segoe UI'; font-weight: bold;
                    font-size: 13px; border-radius: 4px; padding: 6px 12px; border: 1px solid #d35400;
                }
            """)
        self.render_list()

    def toggle_favorite(self):
        sender = self.sender()
        card = sender.parent()
        idx = card.index
        self.history[idx]["favorite"] = not self.history[idx].get("favorite", False)
        _save_history(self.history)
        self.render_list()

    def delete_record(self):
        sender = self.sender()
        card = sender.parent()
        idx = card.index
        del self.history[idx]
        _save_history(self.history)
        self.render_list()

    def clear_history_action(self):
        fav_count = sum(1 for h in self.history if h.get("favorite", False))
        msg = f"Удалить все обычные записи?\nИзбранные ({fav_count}) останутся." if fav_count > 0 else "Вы уверены, что хотите удалить всю историю?"
        
        reply = QMessageBox.question(self, 'Очистка', msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            clear_history()
            self.history = load_history()
            self.render_list()

def open_history_window(root):
    """Открывает окно истории."""
    app = get_qapp()
    dialog = HistoryDialog()
    dialog.exec()