from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QListWidget, QListWidgetItem, QPlainTextEdit, QMessageBox, 
                               QInputDialog, QWidget, QSplitter)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont
from core.qt_utils import get_qapp

class PromptEditorDialog(QDialog):
    def __init__(self, prompts_dict, active_prompt_name, on_save_callback):
        super().__init__()
        self.prompts_dict = prompts_dict.copy() # Работаем с копией, чтобы можно было отменить
        self.active_name = active_prompt_name
        self.on_save_callback = on_save_callback
        self.current_selected_name = active_prompt_name

        self.setWindowTitle("Менеджер промтов")
        self.resize(750, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #cccccc; font-family: 'Segoe UI'; font-size: 13px; }
            QListWidget { 
                background-color: #252525; color: #ffffff; border: 1px solid #333; 
                border-radius: 4px; padding: 5px; font-family: 'Segoe UI'; font-size: 13px;
            }
            QListWidget::item { padding: 5px; border-radius: 3px; }
            QListWidget::item:selected { background-color: #3a3a3a; color: #4CAF50; font-weight: bold; }
            QPlainTextEdit { 
                background-color: #2d2d2d; color: #ffffff; border: 1px solid #444; 
                border-radius: 4px; padding: 8px; font-family: 'Segoe UI'; font-size: 13px;
            }
            QPushButton { 
                background-color: #2d2d2d; color: white; border: 1px solid #444; 
                border-radius: 4px; padding: 6px 12px; font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton#btn_new { border-color: #2196f3; }
            QPushButton#btn_new:hover { background-color: #1e3a5f; }
            QPushButton#btn_del { border-color: #f44336; }
            QPushButton#btn_del:hover { background-color: #5f1e1e; }
            QPushButton#btn_save { 
                background-color: #4CAF50; color: white; border: none; font-weight: bold; font-size: 14px;
            }
            QPushButton#btn_save:hover { background-color: #45a049; }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Используем Splitter для возможности растягивать панели
        splitter = QSplitter(Qt.Horizontal)
        
        # ==========================================
        # ЛЕВАЯ ПАНЕЛЬ (Список)
        # ==========================================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        left_layout.addWidget(QLabel("Сохраненные промты:"))
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_select)
        left_layout.addWidget(self.list_widget)
        
        # Кнопки под списком
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("➕ Новый")
        self.btn_new.setObjectName("btn_new")
        self.btn_new.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_new.setFixedHeight(35)
        self.btn_new.clicked.connect(self.new_prompt)
        
        self.btn_del = QPushButton("🗑 Удалить")
        self.btn_del.setObjectName("btn_del")
        self.btn_del.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_del.setFixedHeight(35)
        self.btn_del.clicked.connect(self.delete_prompt)
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_del)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)

        # ==========================================
        # ПРАВАЯ ПАНЕЛЬ (Редактор)
        # ==========================================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        right_layout.addWidget(QLabel("Текст промта:"))
        
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Напишите здесь инструкцию для нейросети...")
        right_layout.addWidget(self.text_edit)
        
        self.btn_save = QPushButton("💾 Сохранить и использовать")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setFixedHeight(35)
        self.btn_save.clicked.connect(self.save_prompt)
        right_layout.addWidget(self.btn_save)

        splitter.addWidget(right_panel)
        splitter.setHandleWidth(2)
        splitter.setSizes([250, 500]) # Начальная ширина панелей
        
        main_layout.addWidget(splitter)
        
        # Инициализация списка
        self.refresh_list()
        self.load_text_to_editor(self.current_selected_name)

    def refresh_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        for name in self.prompts_dict.keys():
            display_name = f"✅ {name}" if name == self.active_name else f"   {name}"
            item = QListWidgetItem(display_name)
            
            # Сохраняем реальное имя в данных элемента
            item.setData(Qt.UserRole, name)
            
            if name == self.active_name:
                item.setForeground(Qt.green) # Подсветка активного
                
            self.list_widget.addItem(item)
            
            if name == self.current_selected_name:
                self.list_widget.setCurrentItem(item)
                
        self.list_widget.blockSignals(False)

    def on_select(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        name = item.data(Qt.UserRole)
        
        # При клике промт сразу становится активным для следующих записей
        self.current_selected_name = name
        self.active_name = name 
        self.load_text_to_editor(name)
        self.on_save_callback(self.prompts_dict, self.active_name)
        self.refresh_list()

    def load_text_to_editor(self, name):
        self.text_edit.blockSignals(True)
        if name and name in self.prompts_dict:
            self.text_edit.setPlainText(self.prompts_dict[name])
        else:
            self.text_edit.clear()
        self.text_edit.blockSignals(False)

    def new_prompt(self):
        self.list_widget.clearSelection()
        self.current_selected_name = None
        self.text_edit.clear()
        self.text_edit.setFocus()

    def delete_prompt(self):
        if not self.current_selected_name:
            QMessageBox.warning(self, "Внимание", "Выберите промт из списка для удаления.")
            return
            
        reply = QMessageBox.question(self, 'Удаление', 
                                     f"Удалить промт '{self.current_selected_name}'?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            del self.prompts_dict[self.current_selected_name]
            
            # Если удалили активный, делаем активным первый из оставшихся
            if self.active_name == self.current_selected_name:
                self.active_name = list(self.prompts_dict.keys())[0] if self.prompts_dict else ""
                
            self.current_selected_name = self.active_name
            self.on_save_callback(self.prompts_dict, self.active_name)
            self.refresh_list()
            self.load_text_to_editor(self.current_selected_name)

    def save_prompt(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Внимание", "Текст промта не может быть пустым.")
            return

        name = self.current_selected_name
        if name:
            # Обновляем существующий
            self.prompts_dict[name] = text
            self.active_name = name
            self.on_save_callback(self.prompts_dict, self.active_name)
            self.refresh_list()
            QMessageBox.information(self, "Сохранено", f"Промт '{name}' обновлен и выбран!")
        else:
            # Создаем новый
            new_name, ok = QInputDialog.getText(self, "Новый промт", "Введите название для этого промта:")
            if ok and new_name.strip():
                new_name = new_name.strip()
                if new_name in self.prompts_dict:
                    QMessageBox.critical(self, "Ошибка", "Промт с таким названием уже существует.")
                    return
                    
                self.prompts_dict[new_name] = text
                self.active_name = new_name
                self.current_selected_name = new_name
                self.on_save_callback(self.prompts_dict, self.active_name)
                self.refresh_list()
                QMessageBox.information(self, "Сохранено", f"Создан новый промт '{new_name}'!")


def open_prompt_window(root, prompts_dict, active_prompt_name, on_save_callback):
    """Открывает окно менеджера промтов."""
    app = get_qapp()
    dialog = PromptEditorDialog(prompts_dict, active_prompt_name, on_save_callback)
    dialog.exec()