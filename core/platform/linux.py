import time
from pynput.keyboard import Controller, Key
from .base import BasePlatform
from pynput import keyboard

class LinuxPlatform(BasePlatform):
    def __init__(self):
        self._kbd = keyboard.Controller()
        self._listener = None

    def _combo(self, *keys, hold: float = 0.01, gap: float = 0.01) -> None:
        for k in keys:
            self._kbd.press(k)
            time.sleep(gap)
        time.sleep(hold)
        for k in reversed(keys):
            self._kbd.release(k)
            time.sleep(gap)

    def send_copy(self, method: str = "insert") -> None:
        if method == "ctrl_c":
            self._combo(Key.ctrl_l, 'c')
        else:
            self._combo(Key.ctrl_l, Key.insert)

    def send_paste(self) -> None:
        self._combo(Key.ctrl_l, 'v', hold=0.02)

    def send_select_prev_char(self) -> None:
        self._combo(Key.shift, Key.left)

    def send_unselect_prev_char(self) -> None:
        self._combo(Key.shift, Key.right)

    def setup_overlay_window(self, tk_root) -> None:
        # На Linux `overrideredirect(True)` (уже в ui.py) не даёт WM забирать фокус.
        # `-topmost` работает на X11. Дополнительных ctypes-манипуляций не нужно.
        try:
            tk_root.update_idletasks()
            tk_root.wm_attributes('-topmost', True)
        except Exception:
            pass
    def start_key_listener(self, on_press_cb, on_release_cb) -> None:
        self._listener = keyboard.Listener(
            on_press=on_press_cb, 
            on_release=on_release_cb
        )
        self._listener.daemon = True
        self._listener.start()

    def stop_key_listener(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None