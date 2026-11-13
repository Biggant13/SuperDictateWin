import sys
import os
import winreg

APP_NAME = "SuperDictate"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def _get_exe_command() -> str:
    """Возвращает правильную команду для запуска (для exe или для скрипта)."""
    if getattr(sys, 'frozen', False):
        # Если запущено из собранного .exe
        return f'"{sys.executable}"'
    else:
        # Если запущено из исходников (python main.py)
        script_path = os.path.abspath(sys.argv[0])
        return f'"{sys.executable}" "{script_path}"'

def is_enabled() -> bool:
    """Проверяет, включен ли автозапуск."""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False

def set_enabled(enabled: bool) -> None:
    """Включает или выключает автозапуск."""
    if sys.platform != "win32":
        return
        
    try:
        # Открываем ключ реестра для записи
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        if enabled:
            cmd = _get_exe_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass # Записи и так нет
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[Autostart] Ошибка при изменении реестра: {e}")