from abc import ABC, abstractmethod

class BasePlatform(ABC):
    """Абстракция над платформозависимыми операциями."""

    @abstractmethod
    def send_copy(self) -> None:
        """Симулировать Ctrl+C."""

    @abstractmethod
    def send_paste(self) -> None:
        """Симулировать Ctrl+V."""

    @abstractmethod
    def send_select_prev_char(self) -> None:
        """Симулировать Shift+Left (выделить символ слева от курсора)."""

    @abstractmethod
    def send_unselect_prev_char(self) -> None:
        """Симулировать Shift+Right (снять выделение)."""

    @abstractmethod
    def setup_overlay_window(self, tk_root) -> None:
        """Настроить окно оверлея: не забирает фокус, скрыто из taskbar, topmost."""