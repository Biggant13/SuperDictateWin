import platform as _py_platform
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
            from .linux import LinuxPlatform
            _instance = LinuxPlatform()
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
    return _instance