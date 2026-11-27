import time
import ctypes
from ctypes import wintypes
from pynput import keyboard
from core.platform import get_platform
import pyperclip

# --- WinAPI константы для SendInput ---
user32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
VK_CONTROL = 0x11
VK_V = 0x56

HALLUCINATIONS = {
    "редактор субтитров", "корректор", "субтитры", "продолжение следует",
    "спасибо за просмотр", "подписывайтесь на канал", "dimatorzok", "опочки"
}

# --- Структуры для SendInput ---
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", Input_I)]

def _send_key_input(vk, up=False):
    """Отправляет нажатие клавиши через SendInput (надёжнее, чем keybd_event)."""
    flags = KEYEVENTF_KEYUP if up else 0
    scan_code = user32.MapVirtualKeyW(vk, 0)
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    if scan_code == 0:
        ii_.ki = KeyBdInput(vk, 0, flags, 0, ctypes.pointer(extra))
    else:
        ii_.ki = KeyBdInput(0, scan_code, flags | KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def _clipboard_copy_verified(text: str, attempts: int = 6) -> bool:
    """Пишет в буфер через pyperclip и ПРОВЕРЯЕТ, что текст реально там."""
    for _ in range(attempts):
        try:
            pyperclip.copy(text)
        except Exception:
            time.sleep(0.06)
            continue
        time.sleep(0.04)
        try:
            if pyperclip.paste() == text:
                return True
        except Exception:
            pass
        time.sleep(0.06)
    return False

def _map_key(name):
    name = name.strip().lower()
    mods = {
        "ctrl": keyboard.Key.ctrl_l, "control": keyboard.Key.ctrl_l,
        "alt": keyboard.Key.alt_l, "shift": keyboard.Key.shift,
        "win": keyboard.Key.cmd_l, "super": keyboard.Key.cmd_l,
        "cmd": keyboard.Key.cmd_l, "windows": keyboard.Key.cmd_l
    }
    if name in mods: return mods[name]
    special = {
        "space": keyboard.Key.space, "enter": keyboard.Key.enter,
        "return": keyboard.Key.enter, "tab": keyboard.Key.tab,
        "esc": keyboard.Key.esc, "escape": keyboard.Key.esc,
        "backspace": keyboard.Key.backspace, "capslock": keyboard.Key.caps_lock,
        "insert": keyboard.Key.insert, "delete": keyboard.Key.delete,
        "home": keyboard.Key.home, "end": keyboard.Key.end,
        "pageup": keyboard.Key.page_up, "pagedown": keyboard.Key.page_down,
        "up": keyboard.Key.up, "down": keyboard.Key.down,
        "left": keyboard.Key.left, "right": keyboard.Key.right
    }
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
    """Симулирует Ctrl+V через SendInput с полным сбросом модификаторов."""
    # Сбрасываем залипшие модификаторы
    for vk in [VK_CONTROL, 0x12, 0x10]:  # Ctrl, Alt, Shift
        _send_key_input(vk, up=True)
    time.sleep(0.03)

    _send_key_input(VK_CONTROL)
    time.sleep(0.02)
    _send_key_input(VK_V)
    time.sleep(0.05)
    _send_key_input(VK_V, up=True)
    time.sleep(0.02)
    _send_key_input(VK_CONTROL, up=True)

def get_context(copy_method: str = "insert") -> tuple:
    plat = get_platform()
    old_clip = ""
    try: old_clip = pyperclip.paste()
    except Exception: pass

    try: pyperclip.copy("")
    except Exception: pass
    time.sleep(0.05)

    # 1. Проверяем выделение
    plat.send_copy(method=copy_method)
    time.sleep(0.15)

    selected_text = ""
    try: selected_text = pyperclip.paste()
    except Exception: pass

    if selected_text and selected_text.strip():
        try: pyperclip.copy(old_clip)
        except Exception: pass
        time.sleep(0.05)
        return True, selected_text

    # 2. Выделения нет — берём 1 символ слева
    plat.send_select_prev_char()
    time.sleep(0.1)
    plat.send_copy(method=copy_method)
    time.sleep(0.15)

    prev_char = ""
    try: prev_char = pyperclip.paste()
    except Exception: pass

    plat.send_unselect_prev_char()
    time.sleep(0.05)

    try: pyperclip.copy(old_clip)
    except Exception: pass
    time.sleep(0.05)
    return False, prev_char

def format_text(text: str, has_selection: bool, context_data: str = "") -> str:
    text = text.replace('\n', ' ').strip()
    if not text:
        return ""
    if has_selection:
        ends_with_space = context_data.endswith(" ")
        trailing_punct = ""
        clean_context = context_data.strip()
        while clean_context and clean_context[-1] in ".,!?;:":
            trailing_punct = clean_context[-1] + trailing_punct
            clean_context = clean_context[:-1]
        text = text.rstrip('.,!?;:')
        if clean_context and clean_context[0].isupper():
            if text and not text.isupper():
                text = text[0].upper() + text[1:]
        else:
            if text and text[0].isupper() and not text.isupper():
                text = text[0].lower() + text[1:]
        result = text + trailing_punct
        if ends_with_space:
            result += " "
        return result
    else:
        prev_char = context_data
        if prev_char == "" or prev_char == "\n":
            if text and not text.isupper():
                text = text[0].upper() + text[1:]
            return text + " "
        elif prev_char == " ":
            return text + " "
        elif prev_char.isalnum():
            text = text.rstrip('.,!?;:')
            if text and text[0].isupper() and not text.isupper():
                text = text[0].lower() + text[1:]
            return " " + text + " "
        elif prev_char in ",;:":
            text = text.rstrip('.,!?;:')
            if text and text[0].isupper() and not text.isupper():
                text = text[0].lower() + text[1:]
            return " " + text
        elif prev_char in ".!?":
            text = text.rstrip('.,!?;:')
            if text and not text.isupper():
                text = text[0].upper() + text[1:]
            return " " + text + " "
        else:
            return " " + text + " "