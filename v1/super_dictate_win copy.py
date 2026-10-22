"""
SuperDictate для Windows — локальная диктовка по горячей клавише.
Оверлей "Идёт запись" поверх всех окон.
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
from faster_whisper import WhisperModel
from pynput import keyboard
import pyperclip

# ─── Пути ─────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "hotkey": "f9",
    "model_size": "base",
    "language": "ru",
    "overlay_position": "bottom"   # "bottom" или "top"
}

# ─── Настройки ────────────────────────────────────────────────
HOTKEY_STR = "f9"
MODEL_SIZE = "base"
LANGUAGE = "ru"
OVERLAY_POSITION = "bottom"

SAMPLE_RATE = 16000
CHANNELS = 1
DEVICE = None

# ─── Глобальное состояние ─────────────────────────────────────
_recording = False
_audio_queue = queue.Queue()
_stream = None
_model = None
_processing = False
_pressed = set()
_hotkey_set = set()


# ─── Работа с config.json ─────────────────────────────────────
def load_config():
    global HOTKEY_STR, MODEL_SIZE, LANGUAGE, OVERLAY_POSITION
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"[SuperDictate] Создан файл настроек: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    HOTKEY_STR = str(cfg.get("hotkey", DEFAULT_CONFIG["hotkey"])).lower().strip()
    MODEL_SIZE = str(cfg.get("model_size", DEFAULT_CONFIG["model_size"]))
    lang = str(cfg.get("language", DEFAULT_CONFIG["language"])).lower()
    LANGUAGE = None if lang == "auto" else lang
    OVERLAY_POSITION = str(cfg.get("overlay_position", "bottom")).lower()

    print(f"[SuperDictate] Горячая клавиша: {HOTKEY_STR}")
    print(f"[SuperDictate] Модель: {MODEL_SIZE}, язык: {LANGUAGE or 'auto'}")
    print(f"[SuperDictate] Позиция оверлея: {OVERLAY_POSITION}")


# ─── Разбор строки горячей клавиши ────────────────────────────
def _map_key(name):
    name = name.strip().lower()
    mods = {
        "ctrl": keyboard.Key.ctrl_l,
        "control": keyboard.Key.ctrl_l,
        "alt": keyboard.Key.alt_l,
        "shift": keyboard.Key.shift,
        "win": keyboard.Key.cmd_l,
        "super": keyboard.Key.cmd_l,
        "cmd": keyboard.Key.cmd_l,
        "windows": keyboard.Key.cmd_l,
    }
    if name in mods:
        return mods[name]

    special = {
        "space": keyboard.Key.space,
        "enter": keyboard.Key.enter,
        "return": keyboard.Key.enter,
        "tab": keyboard.Key.tab,
        "esc": keyboard.Key.esc,
        "escape": keyboard.Key.esc,
        "backspace": keyboard.Key.backspace,
        "capslock": keyboard.Key.caps_lock,
        "insert": keyboard.Key.insert,
        "delete": keyboard.Key.delete,
        "home": keyboard.Key.home,
        "end": keyboard.Key.end,
        "pageup": keyboard.Key.page_up,
        "pagedown": keyboard.Key.page_down,
        "up": keyboard.Key.up,
        "down": keyboard.Key.down,
        "left": keyboard.Key.left,
        "right": keyboard.Key.right,
    }
    if name in special:
        return special[name]

    if len(name) >= 2 and name[0] == "f" and name[1:].isdigit():
        num = int(name[1:])
        if 1 <= num <= 24:
            return getattr(keyboard.Key, f"f{num}")

    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)

    return None


def parse_hotkey(s):
    parts = [p for p in s.split("+") if p.strip()]
    keys = set()
    for p in parts:
        k = _map_key(p)
        if k is None:
            raise ValueError(f"Неизвестная клавиша в hotkey: '{p}'")
        keys.add(k)
    if not keys:
        raise ValueError("Пустая строка hotkey в config.json")
    return keys


def _normalize(key):
    if key == keyboard.Key.ctrl:
        return keyboard.Key.ctrl_l
    if key == keyboard.Key.alt:
        return keyboard.Key.alt_l
    if key == keyboard.Key.shift:
        return keyboard.Key.shift
    if key == keyboard.Key.cmd:
        return keyboard.Key.cmd_l
    return key


# ─── Загрузка модели ──────────────────────────────────────────
def load_model():
    global _model
    print(f"[SuperDictate] Загрузка модели '{MODEL_SIZE}'...")
    _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("[SuperDictate] Модель готова.")


# ─── Захват аудио ─────────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[audio] {status}", file=sys.stderr)
    if _recording:
        _audio_queue.put(indata.copy())


def start_recording():
    global _stream, _recording
    if _recording:
        return
    _audio_queue.queue.clear()
    _recording = True
    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE,
        callback=audio_callback,
    )
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


# ─── Транскрипция и вставка ───────────────────────────────────
# ─── Транскрипция и вставка ───────────────────────────────────
# Список типичных галлюцинаций Whisper на тишине (можно дополнять).
HALLUCINATIONS = {
    "редактор субтитров",
    "корректор",
    "субтитры",
    "продолжение следует",
    "спасибо за просмотр",
    "подписывайтесь на канал",
    "dimatorzok",
    "опочки",
}

def _is_hallucination(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 2:
        return True
    for marker in HALLUCINATIONS:
        if marker in t:
            return True
    return False


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

        # ── Проверка громкости: если RMS ниже порога — это тишина.
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))
        print(f"[SuperDictate] RMS={rms:.5f} peak={peak:.4f}")

        # Порог RMS: тишина/фоновый шум обычно < 0.005.
        # Если хочешь чувствительнее — уменьши до 0.003.
        if rms < 0.003 or peak < 0.01:
            print("[SuperDictate] Тишина — пропускаю.")
            return

        print("[SuperDictate] 🔄 Распознавание...")
        segments, info = _model.transcribe(
            audio,
            language=LANGUAGE,
            beam_size=5,
            vad_filter=True,                        # Silero VAD внутри faster-whisper
            vad_parameters=dict(
                min_silence_duration_ms=500,        # 0.5 c тишины = граница фразы
                speech_pad_ms=200,
            ),
            no_speech_threshold=0.6,                # выше — строже к «речи»
            log_prob_threshold=-1.0,                # отсеиваем маловероятные сегменты
            condition_on_previous_text=False,       # ВАЖНО: убирает "залипание" галлюцинаций
        )

        pieces = []
        for seg in segments:
            # Дополнительно отсеиваем сегменты без речи
            if getattr(seg, "no_speech_prob", 0) > 0.6:
                continue
            pieces.append(seg.text.strip())

        text = " ".join(pieces).strip()

        if not text:
            print("[SuperDictate] Пустой результат.")
            return

        if _is_hallucination(text):
            print(f"[SuperDictate] Похоже на галлюцинацию, пропускаю: {text!r}")
            return

        print(f"[SuperDictate] 📝 {text}")
        pyperclip.copy(text)
        time.sleep(0.05)
        _press_ctrl_v()

    except Exception as e:
        print(f"[SuperDictate] Ошибка: {e}", file=sys.stderr)
    finally:
        _processing = False


def _press_ctrl_v():
    VK_CONTROL = 0x11
    VK_V = 0x56
    KEYEVENTF_KEYUP = 0x0002
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


# ─── Оверлей ──────────────────────────────────────────────────
class RecordingOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)              # без рамки и заголовка
        self.root.attributes("-topmost", True)        # поверх всех окон
        self.root.attributes("-alpha", 0.9)           # лёгкая прозрачность
        self.root.configure(bg="#202020")
        self.root.attributes("-toolwindow", True)     # не в панели задач

        # Размеры и позиция
        w, h = 210, 46
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        if OVERLAY_POSITION == "top":
            y = 60
        else:
            y = sh - h - 80                            # над панелью задач
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Внутренняя рамка для скруглённого вида
        frame = tk.Frame(self.root, bg="#202020", highlightthickness=1,
                         highlightbackground="#555555")
        frame.pack(fill="both", expand=True)

        label = tk.Label(
            frame,
            text="🔴  Идёт запись...",
            fg="#ffffff",
            bg="#202020",
            font=("Segoe UI", 12, "bold"),
        )
        label.pack(expand=True, fill="both")

        # Windows-специфичное: окно не должно забирать фокус
        self.root.update_idletasks()
        GA_ROOT = 2
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_TOPMOST    = 0x00000008
        user32 = ctypes.windll.user32
        hwnd = user32.GetAncestor(self.root.winfo_id(), GA_ROOT)
        if hwnd:
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
            )

        self.root.withdraw()   # изначально скрыто
        self._visible = False
        self._poll()

    def _poll(self):
        global _recording
        if _recording and not self._visible:
            self.root.deiconify()
            self._visible = True
        elif not _recording and self._visible:
            self.root.withdraw()
            self._visible = False
        self.root.after(50, self._poll)   # опрос 20 раз в секунду

    def run(self):
        # Чтобы Ctrl+C работал внутри mainloop
        def _tick():
            self.root.after(200, _tick)
        _tick()
        self.root.mainloop()


# ─── Обработчики клавиш ───────────────────────────────────────
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


# ─── Точка входа ──────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  SuperDictate для Windows")
    print("=" * 50)

    load_config()

    global _hotkey_set
    try:
        _hotkey_set = parse_hotkey(HOTKEY_STR)
    except Exception as e:
        print(f"[SuperDictate] Ошибка в hotkey: {e}")
        sys.exit(1)

    # Модель грузим до старта UI — так пользователь не увидит "Идёт запись"
    # раньше, чем модель готова.
    load_model()

    # Слушатель клавиш — в отдельном потоке
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    # Оверлей — в главном потоке (tkinter требует main thread)
    overlay = RecordingOverlay()

    # Корректная обработка Ctrl+C
    def _sigint(sig, frame):
        print("\n[SuperDictate] Выход.")
        try:
            listener.stop()
        except Exception:
            pass
        overlay.root.quit()
    signal.signal(signal.SIGINT, _sigint)

    overlay.run()


if __name__ == "__main__":
    main()