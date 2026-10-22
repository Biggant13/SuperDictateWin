"""
SuperDictate для Windows — локальная диктовка на GigaAM v3.
F9 (удержание) — запись с микрофона → вставка в активное окно.
"""
import os
import sys
import json
import signal
import threading
import time
import queue
import ctypes
import tkinter as tk
import numpy as np
import sounddevice as sd
import onnx_asr
from pynput import keyboard
import pyperclip
from PIL import Image, ImageDraw
import pystray

# ─── Пути ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "superdictate.log")

DEFAULT_CONFIG = {
    "hotkey": "f9",
    "model_name": "gigaam-v3-e2e-rnnt",
    "model_path": "",
    "language": "ru",
    "overlay_position": "bottom",
}

# ─── Настройки ───────────────────────────────────────────────
HOTKEY_STR = "f9"
MODEL_NAME = "gigaam-v3-e2e-rnnt"
LANGUAGE = "ru"
OVERLAY_POSITION = "bottom"

SAMPLE_RATE = 16000
CHANNELS = 1
DEVICE = None

# ─── Состояние ───────────────────────────────────────────────
_recording = False
_audio_queue = queue.Queue()
_stream = None
_model = None
_processing = False
_pressed = set()
_hotkey_set = set()
_tray_icon = None
_config = {}


# ─── Перенаправление вывода в лог для .exe ───────────────────
def _setup_logging():
    """Перенаправляет stdout/stderr в файл, если запущены как .exe без консоли."""
    if getattr(sys, "frozen", False) and sys.stdout is None:
        try:
            log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
            sys.stdout = log_file
            sys.stderr = log_file
        except Exception:
            pass


# ─── Конфиг ──────────────────────────────────────────────────
def load_config():
    global HOTKEY_STR, MODEL_NAME, LANGUAGE, OVERLAY_POSITION, _config
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"[SuperDictate] Создан файл: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _config = json.load(f)

    HOTKEY_STR = str(_config.get("hotkey", DEFAULT_CONFIG["hotkey"])).lower().strip()
    MODEL_NAME = str(_config.get("model_name", DEFAULT_CONFIG["model_name"]))
    lang = str(_config.get("language", DEFAULT_CONFIG["language"])).lower()
    LANGUAGE = None if lang == "auto" else lang
    OVERLAY_POSITION = str(_config.get("overlay_position", "bottom")).lower()

    print(f"[SuperDictate] Горячая клавиша: {HOTKEY_STR}")
    print(f"[SuperDictate] Модель: {MODEL_NAME}")
    print(f"[SuperDictate] Оверлей: {OVERLAY_POSITION}")


# ─── Клавиши ─────────────────────────────────────────────────
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


def _normalize(key):
    if key == keyboard.Key.ctrl: return keyboard.Key.ctrl_l
    if key == keyboard.Key.alt: return keyboard.Key.alt_l
    if key == keyboard.Key.shift: return keyboard.Key.shift
    if key == keyboard.Key.cmd: return keyboard.Key.cmd_l
    return key


# ─── Модель GigaAM ──────────────────────────────────────────
def load_model():
    global _model

    candidates = []

    # 1. Путь из конфига
    cfg_path = _config.get("model_path", "")
    if cfg_path:
        p = cfg_path
        if not os.path.isabs(p):
            p = os.path.join(BASE_DIR, p)
        candidates.append(p)

    # 2. Авто-поиск рядом с .exe
    candidates.append(os.path.join(BASE_DIR, "gigaam-v3-e2e-rnnt-onnx"))
    candidates.append(os.path.join(BASE_DIR, "gigaam-v3-e2e-rnnt"))

    chosen = None
    for c in candidates:
        c_norm = os.path.normpath(c)
        # Проверяем, что это папка и в ней есть onnx-файлы
        exists = os.path.isdir(c_norm) and any(
            f.endswith(".onnx") for f in os.listdir(c_norm)
        )
        print(f"[SuperDictate] Проверка модели: {c_norm} → {'OK' if exists else 'нет'}")
        if exists:
            chosen = c_norm
            break

    if chosen:
        print(f"[SuperDictate] Загрузка GigaAM из локальной папки: '{chosen}'")
        try:
            _model = onnx_asr.load_model(MODEL_NAME, chosen)
            print("[SuperDictate] Модель загружена из локальной папки.")
            return
        except Exception as e:
            print(f"[SuperDictate] Не удалось загрузить локальную модель: {e}", file=sys.stderr)
            print("[SuperDictate] Пробую скачать с Hugging Face...", file=sys.stderr)
    else:
        print("[SuperDictate] Локальная папка с моделью не найдена рядом с .exe.")
        print("[SuperDictate] Скачиваю с Hugging Face...")

    _model = onnx_asr.load_model(MODEL_NAME)
    print("[SuperDictate] Модель готова.")


# ─── Захват аудио ───────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[audio] {status}", file=sys.stderr)
    if _recording:
        mono = indata.astype(np.float32)
        if mono.ndim == 2 and mono.shape[1] > 1:
            mono = mono.mean(axis=1, keepdims=True)
        _audio_queue.put(mono)


def start_recording():
    global _stream, _recording
    if _recording:
        return
    _audio_queue.queue.clear()
    _recording = True
    _stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                             dtype="float32", device=DEVICE, callback=audio_callback)
    _stream.start()
    print("[SuperDictate] 🎤 Запись...")


def stop_recording():
    global _stream, _recording
    if not _recording:
        return
    _recording = False
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None
    print("[SuperDictate] ⏹ Запись остановлена.")


# ─── Транскрипция + вставка ─────────────────────────────────
def transcribe_and_paste():
    global _processing
    if _processing:
        return
    _processing = True
    try:
        chunks = []
        while not _audio_queue.empty():
            chunks.append(_audio_queue.get())
        if not chunks:
            print("[SuperDictate] Нет аудио.")
            return
        audio = np.concatenate(chunks, axis=0).flatten().astype(np.float32)
        if len(audio) < SAMPLE_RATE * 0.3:
            print("[SuperDictate] Слишком короткая запись.")
            return

        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < 0.003:
            print(f"[SuperDictate] Тишина (RMS={rms:.5f}) — пропускаю.")
            return

        print("[SuperDictate] 🔄 Распознавание GigaAM...")
        text = _model.recognize(audio).strip()

        if not text:
            print("[SuperDictate] Пустой результат.")
            return

        text = text + " "
        print(f"[SuperDictate] 📝 {text}")
        pyperclip.copy(text)
        time.sleep(0.05)
        _press_ctrl_v()

    except Exception as e:
        print(f"[SuperDictate] Ошибка: {e}", file=sys.stderr)
    finally:
        _processing = False


def _press_ctrl_v():
    VK_CONTROL, VK_V, KEYEVENTF_KEYUP = 0x11, 0x56, 0x0002
    u = ctypes.windll.user32
    u.keybd_event(VK_CONTROL, 0, 0, 0)
    u.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    u.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    u.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


# ─── Оверлей ────────────────────────────────────────────────
class RecordingOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="#202020")
        self.root.attributes("-toolwindow", True)

        w, h = 200, 46
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = 60 if OVERLAY_POSITION == "top" else sh - h - 80
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(self.root, bg="#202020", highlightthickness=1,
                         highlightbackground="#555555")
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="🔴  Идёт запись...", fg="#ffffff", bg="#202020",
                 font=("Segoe UI", 12, "bold")).pack(expand=True, fill="both")

        self.root.update_idletasks()
        GWL_EXSTYLE, WS_EX_NOACTIVATE = -20, 0x08000000
        WS_EX_TOOLWINDOW, WS_EX_TOPMOST = 0x00000080, 0x00000008
        u = ctypes.windll.user32
        hwnd = u.GetAncestor(self.root.winfo_id(), 2)
        if hwnd:
            ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)

        self.root.withdraw()
        self._visible = False
        self._poll()

    def _poll(self):
        if _recording and not self._visible:
            self.root.deiconify()
            self._visible = True
        elif not _recording and self._visible:
            self.root.withdraw()
            self._visible = False
        self.root.after(50, self._poll)

    def run(self):
        self.root.mainloop()


# ─── Обработчики ────────────────────────────────────────────
def on_press(key):
    nk = _normalize(key)
    _pressed.add(nk)
    if not _recording and _hotkey_set.issubset(_pressed):
        start_recording()


def on_release(key):
    nk = _normalize(key)
    _pressed.discard(nk)
    if _recording and nk in _hotkey_set:
        stop_recording()
        threading.Thread(target=transcribe_and_paste, daemon=True).start()


# ─── Трей и main ────────────────────────────────────────────
def _make_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=(220, 50, 50, 255))
    d.ellipse((22, 18, 42, 38), fill=(255, 255, 255, 255))
    d.rectangle((28, 34, 36, 46), fill=(255, 255, 255, 255))
    return img


def main():
    _setup_logging()

    print("=" * 50)
    print("  SuperDictate для Windows (GigaAM v3)")
    print("=" * 50)

    load_config()

    global _hotkey_set, _tray_icon
    try:
        _hotkey_set = parse_hotkey(HOTKEY_STR)
    except Exception as e:
        print(f"[SuperDictate] Ошибка в hotkey: {e}")
        sys.exit(1)

    load_model()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    overlay = RecordingOverlay()

    def _shutdown():
        try: listener.stop()
        except Exception: pass
        try: overlay.root.after(0, overlay.root.quit)
        except Exception: pass

    def _start_tray():
        global _tray_icon
        def on_quit(icon, item):
            icon.stop()
            _shutdown()
        menu = pystray.Menu(
            pystray.MenuItem("SuperDictate (GigaAM)", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", on_quit),
        )
        _tray_icon = pystray.Icon("superdictate", _make_icon_image(),
                                  "SuperDictate", menu)
        _tray_icon.run()

    threading.Thread(target=_start_tray, daemon=True).start()

    def _sigint(sig, frame):
        print("\n[SuperDictate] Выход.")
        try:
            if _tray_icon is not None:
                _tray_icon.stop()
        except Exception: pass
        _shutdown()
    signal.signal(signal.SIGINT, _sigint)

    try:
        overlay.run()
    finally:
        if _tray_icon is not None:
            try: _tray_icon.stop()
            except Exception: pass


if __name__ == "__main__":
    main()