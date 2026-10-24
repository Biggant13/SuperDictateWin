import ctypes
import time
from .base import BasePlatform

VK_CONTROL = 0x11
VK_C = 0x43
VK_V = 0x56
VK_SHIFT = 0x10
VK_LEFT = 0x25
VK_RIGHT = 0x27
KEYEVENTF_KEYUP = 0x0002

class WindowsPlatform(BasePlatform):
    def _send_key(self, vk: int, up: bool = False) -> None:
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP if up else 0, 0)
        time.sleep(0.01)

    def send_copy(self) -> None:
        self._send_key(VK_CONTROL)
        self._send_key(VK_C)
        self._send_key(VK_C, up=True)
        self._send_key(VK_CONTROL, up=True)

    def send_paste(self) -> None:
        u = ctypes.windll.user32
        u.keybd_event(VK_CONTROL, 0, 0, 0)
        u.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.02)
        u.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        u.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def send_select_prev_char(self) -> None:
        self._send_key(VK_SHIFT)
        self._send_key(VK_LEFT)
        self._send_key(VK_LEFT, up=True)
        self._send_key(VK_SHIFT, up=True)

    def send_unselect_prev_char(self) -> None:
        self._send_key(VK_SHIFT)
        self._send_key(VK_RIGHT)
        self._send_key(VK_RIGHT, up=True)
        self._send_key(VK_SHIFT, up=True)

    def setup_overlay_window(self, tk_root) -> None:
        # Скрыть из панели задач / Alt+Tab
        try:
            tk_root.attributes("-toolwindow", True)
        except Exception:
            pass

        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_TOPMOST = 0x00000008

        tk_root.update_idletasks()
        u = ctypes.windll.user32
        hwnd = u.GetAncestor(tk_root.winfo_id(), 2)
        if hwnd:
            ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            u.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
            )