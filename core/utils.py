import time
import ctypes
import pyperclip
from pynput import keyboard

HALLUCINATIONS = {"редактор субтитров", "корректор", "субтитры", "продолжение следует",
                  "спасибо за просмотр", "подписывайтесь на канал", "dimatorzok", "опочки"}

# Коды виртуальных клавиш Windows
VK_CONTROL = 0x11
VK_C = 0x43
VK_SHIFT = 0x10
VK_LEFT = 0x25
VK_RIGHT = 0x27
KEYEVENTF_KEYUP = 0x0002

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
    u = ctypes.windll.user32
    u.keybd_event(VK_CONTROL, 0, 0, 0)
    u.keybd_event(0x56, 0, 0, 0) # VK_V
    time.sleep(0.02)
    u.keybd_event(0x56, 0, KEYEVENTF_KEYUP, 0)
    u.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def _send_key(vk, up=False):
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP if up else 0, 0)
    time.sleep(0.01) # Небольшая пауза, чтобы система успевала обрабатывать

def get_context():
    user32 = ctypes.windll.user32
    old_clip = ""
    try: old_clip = pyperclip.paste()
    except: pass

    # Очищаем буфер
    try: pyperclip.copy("")
    except: pass
    time.sleep(0.05)

    # 1. Проверяем выделение (Ctrl+C)
    _send_key(VK_CONTROL)
    _send_key(VK_C)
    _send_key(VK_C, up=True)
    _send_key(VK_CONTROL, up=True)
    time.sleep(0.15) 
    
    selected_text = ""
    try: selected_text = pyperclip.paste()
    except: pass

    if selected_text and selected_text.strip():
        try: pyperclip.copy(old_clip)
        except: pass
        return True, selected_text

    # 2. Выделения нет. Берем 1 символ СЛЕВА
    _send_key(VK_SHIFT)
    _send_key(VK_LEFT)
    _send_key(VK_LEFT, up=True)
    _send_key(VK_SHIFT, up=True)
    time.sleep(0.1) # Даем редактору выделить символ
    
    _send_key(VK_CONTROL)
    _send_key(VK_C)
    _send_key(VK_C, up=True)
    _send_key(VK_CONTROL, up=True)
    time.sleep(0.15)
    
    prev_char = ""
    try: prev_char = pyperclip.paste()
    except: pass
    
    # Возвращаем курсор ровно на место (снимаем выделение)
    _send_key(VK_SHIFT)
    _send_key(VK_RIGHT)
    _send_key(VK_RIGHT, up=True)
    _send_key(VK_SHIFT, up=True)
    time.sleep(0.05)
    
    try: pyperclip.copy(old_clip)
    except: pass

    return False, prev_char

def format_text(text: str, has_selection: bool, context_data: str = "") -> str:
    # Убираем переносы строк и лишние пробелы по краям
    text = text.replace('\n', ' ').strip()
    if not text:
        return ""

    # РЕЖИМ 1: Замена выделенного слова
    if has_selection:
        ends_with_space = context_data.endswith(" ")
        
        # Сохраняем знаки препинания, которые были в выделении (например, точку или запятую)
        trailing_punct = ""
        clean_context = context_data.strip()
        while clean_context and clean_context[-1] in ".,!?;:":
            trailing_punct = clean_context[-1] + trailing_punct
            clean_context = clean_context[:-1]
            
        # Убираем точку, которую поставила нейросеть
        text = text.rstrip('.,!?;:')
        
        # Выравниваем регистр по первой букве старого слова
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
        
    # РЕЖИМ 2: Обычная вставка (без выделения)
    else:
        prev_char = context_data
        
        # 1. Начало строки или пустое поле
        if prev_char == "" or prev_char == "\n":
            if text and not text.isupper():
                text = text[0].upper() + text[1:]
            return text + " "
            
        # 2. Перед нами ПРОБЕЛ. Доверяем GigaAM (она сама расставит точки и заглавные).
        elif prev_char == " ":
            return text + " "
            
        # 3. Перед нами буква или цифра (вплотную). Надо добавить пробел.
        elif prev_char.isalnum():
            text = text.rstrip('.,!?;:')
            if text and text[0].isupper() and not text.isupper():
                text = text[0].lower() + text[1:]
            return " " + text + " "
            
        # 4. Перед нами запятая, двоеточие, точка с запятой
        elif prev_char in ",;:":
            text = text.rstrip('.,!?;:')
            if text and text[0].isupper() and not text.isupper():
                text = text[0].lower() + text[1:]
            return " " + text  # Пробел только спереди, чтобы приклеиться к запятой
            
        # 5. Перед нами конец предложения (точка, ! или ?)
        elif prev_char in ".!?":
            text = text.rstrip('.,!?;:')
            if text and not text.isupper():
                text = text[0].upper() + text[1:]
            return " " + text + " "  # Пробелы с обеих сторон
            
        # 6. Любой другой символ (кавычки, скобки и т.д.)
        else:
            return " " + text + " "