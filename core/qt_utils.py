import sys
from PySide6.QtWidgets import QApplication

_qapp = None

def get_qapp():
    """Возвращает единственный экземпляр QApplication."""
    global _qapp
    if _qapp is None:
        _qapp = QApplication.instance()
        if _qapp is None:
            _qapp = QApplication(sys.argv)
    return _qapp