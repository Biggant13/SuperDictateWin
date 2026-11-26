from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QWidget, QFrame, QSizePolicy)
from PySide6.QtCore import Qt
from core.qt_utils import get_qapp

class HelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Как пользоваться")
        self.setFixedSize(500, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { font-family: 'Segoe UI'; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # --- Заголовок ---
        lbl_title = QLabel("SuperDictate")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("Краткая инструкция")
        lbl_subtitle.setStyleSheet("color: #888888; font-size: 13px;")
        lbl_subtitle.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl_subtitle)
        
        main_layout.addSpacing(10)

        # --- Функция для создания блока с клавишей ---
        def add_section(hotkey, title, description, color):
            # Контейнер для одного блока
            section_widget = QWidget()
            section_layout = QHBoxLayout(section_widget)
            section_layout.setContentsMargins(0, 5, 0, 5)
            section_layout.setSpacing(20)

            # Клавиша (слева)
            lbl_key = QLabel(hotkey)
            lbl_key.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
            lbl_key.setFixedWidth(40)
            lbl_key.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            section_layout.addWidget(lbl_key)

            # Текст (справа)
            text_container = QWidget()
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
            text_layout.addWidget(lbl_title)

            lbl_desc = QLabel(description)
            lbl_desc.setStyleSheet("color: #aaaaaa; font-size: 12px;")
            lbl_desc.setWordWrap(True)
            text_layout.addWidget(lbl_desc)

            section_layout.addWidget(text_container, stretch=1)
            main_layout.addWidget(section_widget)

        # --- Добавляем блоки ---
        add_section("F9", "Диктовка (Микрофон)", 
                    "Зажмите клавишу и говорите. Отпустите — текст распознается и вставится в активное окно.", 
                    "#4caf50") # Зеленый

        add_section("F8", "Диктовка (Системный звук)", 
                    "Зажмите клавишу и включите звук на компьютере. Отпустите — звук распознается и вставится текстом.", 
                    "#2196f3") # Синий

        add_section("F7", "Режим встреч (Нажмите 1 раз)", 
                    "Начинает запись встречи (микрофон + система) и разделяет голоса спикеров. Нажмите F7 снова, чтобы остановить. Результат сохранится в 'Папку встреч' (в меню трея).", 
                    "#ff4d4d") # Красный

        # --- Растягивающийся пробел, чтобы подсказка была внизу ---
        main_layout.addStretch()

        # --- Подсказка про промт ---
        hint_frame = QFrame()
        hint_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a1a;
                border: 1px solid #ffa726;
                border-radius: 6px;
            }
        """)
        hint_layout = QVBoxLayout(hint_frame)
        hint_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_hint = QLabel("💡 Выберите Промт в меню трея перед встречей.\nОн добавится в начало файла для нейросети.")
        lbl_hint.setStyleSheet("color: #ffa726; font-size: 12px; font-style: italic; border: none;")
        lbl_hint.setAlignment(Qt.AlignCenter)
        hint_layout.addWidget(lbl_hint)
        
        main_layout.addWidget(hint_frame)


def open_help_window(root):
    """Открывает окно справки."""
    app = get_qapp()
    dialog = HelpDialog()
    dialog.exec()