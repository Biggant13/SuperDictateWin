import platform as _py_platform
import os
from .base import BasePlatform

_instance = None

def get_platform() -> BasePlatform:
    global _instance
    if _instance is None:
        system = _py_platform.system()
        if system == "Windows":
            from .windows import WindowsPlatform
            _instance = WindowsPlatform()
        elif system == "Linux":
            # Проверяем, работаем ли мы под Wayland
            session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
            wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
            
            if session_type == "wayland" or wayland_display:
                try:
                    from .linux_wayland import LinuxWaylandPlatform
                    _instance = LinuxWaylandPlatform()
                    print("[Platform] Обнаружен Wayland. Используется evdev.")
                except ImportError:
                    print("[Platform] Wayland обнаружен, но evdev не установлен. Откат на X11.")
                    from .linux import LinuxPlatform
                    _instance = LinuxPlatform()
            else:
                from .linux import LinuxPlatform
                _instance = LinuxPlatform()
                print("[Platform] Обнаружен X11. Используется pynput.")
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
    return _instance