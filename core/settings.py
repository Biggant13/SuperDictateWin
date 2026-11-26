import sys
import json
import sounddevice as sd
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, 
                               QComboBox, QCheckBox, QPushButton, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from core.config import CONFIG_PATH
from core.autostart import is_enabled, set_enabled
from core.qt_utils import get_qapp

# Синглтон для QApplication, чтобы избежать конфликтов при многократном открытии
_qapp = None

class SettingsDialog(QDialog):
    def __init__(self, parent, current_cfg, on_save_callback):
        super().__init__()
        self.current_cfg = current_cfg
        self.on_save_callback = on_save_callback
        
        self.setWindowTitle("Настройки SuperDictate")
        self.setFixedSize(450, 560)
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
        main_layout.setSpacing(10)

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
        
        current_device_idx = self.current_cfg.get("input_device", "")
        current_device_name = "По умолчанию (системный)"
        
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name = f"{dev['name']} ({i})"
                input_devices.append(name)
                self.device_map[name] = i
                if str(i) == str(current_device_idx):
                    current_device_name = name
                    
        self.combo_device.addItems(input_devices)
        self.combo_device.setCurrentText(current_device_name)
        layout_audio.addWidget(self.combo_device)
        
        lbl_copy = QLabel("Метод копирования контекста:")
        lbl_copy.setToolTip("insert: Ctrl+Insert (безопасно).\nctrl_c: Ctrl+C (классическое, но может убить процесс в терминале).")
        layout_audio.addWidget(lbl_copy)
        
        self.combo_copy = QComboBox()
        self.combo_copy.addItems(["insert", "ctrl_c"])
        self.combo_copy.setCurrentText(self.current_cfg.get("copy_method", "insert"))
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
        self.combo_overlay.setCurrentText(self.current_cfg.get("overlay_position", "bottom"))
        layout_sys.addWidget(self.combo_overlay)
        
        self.cb_sound = QCheckBox("Включить звуковые сигналы")
        self.cb_sound.setToolTip("Короткие звуки (бипы), подтверждающие старт и стоп записи.")
        self.cb_sound.setChecked(self.current_cfg.get("sound_enabled", True))
        layout_sys.addWidget(self.cb_sound)
        
        self.cb_gpu = QCheckBox("Использовать видеокарту (GPU)")
        self.cb_gpu.setToolTip("Ускоряет распознавание. Требуется перезапуск.")
        self.cb_gpu.setChecked(self.current_cfg.get("use_gpu", True))
        layout_sys.addWidget(self.cb_gpu)
        
        self.cb_auto = QCheckBox("Запускать при старте Windows")
        self.cb_auto.setChecked(is_enabled())
        layout_sys.addWidget(self.cb_auto)
        
        main_layout.addWidget(group_sys)

        # Кнопка
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self.save)
        main_layout.addWidget(self.btn_save)

    def save(self):
        new_cfg = self.current_cfg.copy()
        new_cfg["overlay_position"] = self.combo_overlay.currentText()
        new_cfg["sound_enabled"] = self.cb_sound.isChecked()
        new_cfg["use_gpu"] = self.cb_gpu.isChecked()
        new_cfg["copy_method"] = self.combo_copy.currentText()
        
        selected_dev_name = self.combo_device.currentText()
        new_cfg["input_device"] = self.device_map.get(selected_dev_name, "")

        try:
            old_gpu = self.current_cfg.get("use_gpu", True)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, indent=2, ensure_ascii=False)
            
            set_enabled(self.cb_auto.isChecked())
            self.on_save_callback(new_cfg)
            
            gpu_changed = old_gpu != new_cfg["use_gpu"]
            msg = "Настройки сохранены!"
            if gpu_changed:
                msg += "\n\nВы изменили настройку видеокарты. Перезапустите приложение."
            
            QMessageBox.information(self, "Успех", msg)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

def open_settings_window(root, current_cfg, on_save_callback):
    """Открывает окно настроек. Параметр root (Tkinter) игнорируется."""
    app = get_qapp() # Инициализируем Qt, если еще не сделано
    dialog = SettingsDialog(None, current_cfg, on_save_callback)
    dialog.exec()   # Блокирует Tkinter до закрытия окна (это нормально для модальных окон)