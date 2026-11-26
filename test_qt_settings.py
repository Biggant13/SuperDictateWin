import sys
import json
import sounddevice as sd
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QCheckBox, QPushButton, QGroupBox, QWidget)
from PySide6.QtCore import Qt

# Эмулируем конфиг для теста
CONFIG_PATH = "config.json"
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        current_cfg = json.load(f)
except:
    current_cfg = {"input_device": "", "overlay_position": "bottom", "sound_enabled": True, "use_gpu": False}

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки SuperDictate (PySide6)")
        self.setFixedSize(450, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QLabel { color: #cccccc; font-family: 'Segoe UI'; font-size: 13px; }
            QGroupBox { 
                color: #ffffff; font-family: 'Segoe UI'; font-weight: bold; font-size: 13px;
                border: 1px solid #3a3a3a; border-radius: 6px; margin-top: 15px; padding-top: 15px;
                background-color: #252525;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 3px; }
            QComboBox { 
                background-color: #2d2d2d; color: #ffffff; border: 1px solid #444; 
                border-radius: 4px; padding: 4px 8px; min-height: 25px;
            }
            QComboBox QAbstractItemView { background-color: #2d2d2d; color: white; }
            QCheckBox { color: #ffffff; font-family: 'Segoe UI'; font-size: 13px; padding: 5px; }
            QPushButton { 
                background-color: #4CAF50; color: white; border: none; 
                border-radius: 6px; padding: 10px; font-family: 'Segoe UI'; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # --- Блок 1: Аудио и ввод ---
        group_audio = QGroupBox("🎤 Аудио и ввод")
        layout_audio = QVBoxLayout(group_audio)
        
        lbl_mic = QLabel("Микрофон:")
        lbl_mic.setToolTip("Устройство, с которого записывается звук.")
        layout_audio.addWidget(lbl_mic)
        
        self.combo_device = QComboBox()
        devices = sd.query_devices()
        input_devices = ["По умолчанию (системный)"]
        self.device_map = {"По умолчанию (системный)": ""}
        
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name = f"{dev['name']} ({i})"
                input_devices.append(name)
                self.device_map[name] = i
        
        self.combo_device.addItems(input_devices)
        layout_audio.addWidget(self.combo_device)
        
        lbl_copy = QLabel("Метод копирования контекста:")
        lbl_copy.setToolTip("insert: Ctrl+Insert (безопасно).\nctrl_c: Ctrl+C (классическое, но может убить процесс в терминале).")
        layout_audio.addWidget(lbl_copy)
        
        self.combo_copy = QComboBox()
        self.combo_copy.addItems(["insert", "ctrl_c"])
        layout_audio.addWidget(self.combo_copy)
        
        main_layout.addWidget(group_audio)

        # --- Блок 2: Интерфейс и система ---
        group_sys = QGroupBox("⚙️ Интерфейс и система")
        layout_sys = QVBoxLayout(group_sys)
        
        lbl_overlay = QLabel("Позиция оверлея:")
        lbl_overlay.setToolTip("Где показывать плашку.")
        layout_sys.addWidget(lbl_overlay)
        
        self.combo_overlay = QComboBox()
        self.combo_overlay.addItems(["bottom", "top"])
        layout_sys.addWidget(self.combo_overlay)
        
        self.cb_sound = QCheckBox("Включить звуковые сигналы")
        self.cb_sound.setToolTip("Короткие звуки (бипы), подтверждающие старт и стоп записи.")
        layout_sys.addWidget(self.cb_sound)
        
        self.cb_gpu = QCheckBox("Использовать видеокарту (GPU)")
        self.cb_gpu.setToolTip("Ускоряет распознавание. Требуется перезапуск.")
        layout_sys.addWidget(self.cb_gpu)
        
        self.cb_auto = QCheckBox("Запускать при старте Windows")
        layout_sys.addWidget(self.cb_auto)
        
        main_layout.addWidget(group_sys)

        # Кнопка
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self.save_and_close)
        main_layout.addWidget(self.btn_save)

    def save_and_close(self):
        print("Настройки сохранены (тестовый режим)")
        self.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.exec()