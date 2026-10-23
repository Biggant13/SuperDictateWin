import sys
import signal
import threading
from pynput import keyboard

from core.config import load_config
from core.audio import AudioRecorder
from core.transcriber import Transcriber
from core.ui import RecordingOverlay
from core.tray import start_tray
from core.utils import parse_hotkey, normalize_key, get_context

def main():
    print("=" * 50)
    print("  SuperDictate для Windows (GigaAM v3)")
    print("=" * 50)

    cfg = load_config()
    hotkey_set = parse_hotkey(cfg["hotkey"])
    
    print(f"[Main] Горячая клавиша: {cfg['hotkey']}")
    
    # Инициализация компонентов
    audio = AudioRecorder()
    transcriber = Transcriber(cfg)
    transcriber.load_model()
    
    pressed_keys = set()
    processing_flag = [False]

    # --- Колбэки для pynput ---
    def on_press(key):
        nk = normalize_key(key)
        pressed_keys.add(nk)
        if not audio.recording and hotkey_set.issubset(pressed_keys):
            audio.start()

    def on_release(key):
        nk = normalize_key(key)
        pressed_keys.discard(nk)
        
        if audio.recording and nk in hotkey_set:
            audio.stop()
            audio_data = audio.get_audio()
            
            # 1. Считываем контекст (быстро, ~40мс)
            has_selection, prev_char = get_context()
            
            # 2. Запускаем распознавание
            threading.Thread(
                target=transcriber.transcribe_and_paste, 
                args=(audio_data, has_selection, prev_char, processing_flag), 
                daemon=True
            ).start()

    # --- Запуск интерфейса и трея ---
    # --- Запуск интерфейса и трея ---
    overlay = RecordingOverlay(
        is_recording_cb=lambda: audio.recording, 
        is_processing_cb=lambda: processing_flag[0], # <-- Добавили эту строку
        position=cfg["overlay_position"]
    )
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    def _shutdown():
        try: listener.stop()
        except Exception: pass
        try: overlay.root.after(0, overlay.quit)
        except Exception: pass

    start_tray(on_quit=_shutdown)

    def _sigint(sig, frame):
        print("\n[Main] Выход.")
        _shutdown()
    signal.signal(signal.SIGINT, _sigint)

    # Главный цикл tkinter
    try:
        overlay.run()
    finally:
        _shutdown()

if __name__ == "__main__":
    main()