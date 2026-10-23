import time
import ctypes
from pynput import keyboard

HALLUCINATIONS = {"редактор субтитров", "корректор", "субтитры", "продолжение следует",
                  "спасибо за просмотр", "подписывайтесь на канал", "dimatorzok", "опочки"}

def _map_key(name):
    name = name.strip().lower()
    mods = {"ctrl": keyboard.Key.ctrl_l, "control": keyboard.Key.ctrl_l,
            "alt": keyboard.Key.alt_l, "shift": keyboard.Key.shift,
            "win": keyboard.Key.cmd_l, "super": keyboard.Key.cmd_l,
            "cmd": keyboard.Key.cmd_l, "windows": keyboard.Key.cmd_l}
    if name in mods: return mods[name]
    special = {"space": keyboard.Key.space, "enter": keyboard.Key.enter,
               "return": keyboard.Key.enter, "tab": keyboard.Key.tab,
               "esc": keyboard.Key.esc, "escape": keyboard.Key.esc,
               "backspace": keyboard.Key.backspace, "capslock": keyboard.Key.caps_lock,
               "insert": keyboard.Key.insert, "delete": keyboard.Key.delete,
               "home": keyboard.Key.home, "end": keyboard.Key.end,
               "pageup": keyboard.Key.page_up, "pagedown": keyboard.Key.page_down,
               "up": keyboard.Key.up, "down": keyboard.Key.down,
               "left": keyboard.Key.left, "right": keyboard.Key.right}
    if name in special: return special[name]
    if len(name) >= 2 and name[0] == "f" and name[1:].isdigit():
        num = int(name[1:])
        if 1 <= num <= 24: return getattr(keyboard.Key, f"f{num}")
    if len(name) == 1: return keyboard.KeyCode.from_char(name)
    return None

def parse_hotkey(s):
    parts = [p for p in s.split("+") if p.strip()]
    keys = set()
    for p in parts:
        k = _map_key(p)
        if k is None:
            raise ValueError(f"Неизвестная клавиша: '{p}'")
        keys.add(k)
    if not keys:
        raise ValueError("Пустая строка hotkey")
    return keys

def normalize_key(key):
    if key == keyboard.Key.ctrl: return keyboard.Key.ctrl_l
    if key == keyboard.Key.alt: return keyboard.Key.alt_l
    if key == keyboard.Key.shift: return keyboard.Key.shift
    if key == keyboard.Key.cmd: return keyboard.Key.cmd_l
    return key

def is_hallucination(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 2:
        return True
    return any(m in t for m in HALLUCINATIONS)

def press_ctrl_v():
    VK_CONTROL, VK_V, KEYEVENTF_KEYUP = 0x11, 0x56, 0x0002
    u = ctypes.windll.user32
    u.keybd_event(VK_CONTROL, 0, 0, 0)
    u.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    u.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    u.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)