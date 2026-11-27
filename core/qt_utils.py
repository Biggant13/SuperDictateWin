import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

class TrayDispatcher(QObject):
    open_settings = Signal()
    open_history = Signal()
    open_meetings = Signal()
    open_prompt = Signal()
    open_help = Signal()
    open_log = Signal()
    open_transcribe_file = Signal()
    transcribe_done = Signal(str)

dispatcher = TrayDispatcher()

_qapp = None

def get_qapp():
    """Возвращает единственный экземпляр QApplication."""
    global _qapp
    if _qapp is None:
        _qapp = QApplication.instance()
        if _qapp is None:
            _qapp = QApplication(sys.argv)
    return _qapp