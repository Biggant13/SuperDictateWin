from abc import ABC, abstractmethod

class BasePlatform(ABC):
    """Абстракция над платформозависимыми операциями."""

    @abstractmethod
    def send_copy(self) -> None:
        """Симулировать Ctrl+C."""
        pass

    @abstractmethod
    def send_paste(self) -> None:
        """Симулировать Ctrl+V."""
        pass

    @abstractmethod
    def send_select_prev_char(self) -> None:
        """Симулировать Shift+Left (выделить символ слева от курсора)."""
        pass

    @abstractmethod
    def send_unselect_prev_char(self) -> None:
        """Симулировать Shift+Right (снять выделение)."""
        pass

    @abstractmethod
    def setup_overlay_window(self, tk_root) -> None:
        """Настроить окно оверлея: не забирает фокус, скрыто из taskbar, topmost."""
        pass
    
    @abstractmethod
    def start_key_listener(self, on_press_cb, on_release_cb) -> None:
        """Запустить фоновый слушатель клавиатуры."""
        pass

    @abstractmethod
    def stop_key_listener(self) -> None:
        """Остановить слушатель клавиатуры."""
        pass