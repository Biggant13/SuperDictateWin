import sys
import os
import signal
import threading
from pynput import keyboard

from core.logger import setup_logger
logger = setup_logger()

from core.config import load_config
from core.audio import AudioRecorder
from core.transcriber import Transcriber
from core.ui import RecordingOverlay
from core.tray import start_tray
from core.sounds import beep_start, beep_stop
from core.settings import open_settings_window
from core.stats import add_words # <-- Импортируем статистику
from core.utils import parse_hotkey, normalize_key, get_context

def main():
    print("=" * 50)
    print("  SuperDictate для Windows (GigaAM v3)")
    print("=" * 50)

    cfg = load_config()
    hotkey_set = parse_hotkey(cfg["hotkey"])
    
    audio = AudioRecorder()
    transcriber = Transcriber(cfg)
    transcriber.load_model()
    
    pressed_keys = set()
    processing_flag = [False]
    beep_vol = float(cfg.get("beep_volume", 0.05))
    
    sound_state = [cfg.get("sound_enabled", True)]

    def toggle_sound():
        sound_state[0] = not sound_state[0]
        cfg["sound_enabled"] = sound_state[0]
        from core.config import CONFIG_PATH
        import json
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    overlay = RecordingOverlay(
        is_recording_cb=lambda: audio.recording, 
        is_processing_cb=lambda: processing_flag[0], 
        position=cfg["overlay_position"]
    )

    # --- Колбэки для pynput ---
    def on_press(key):
        nk = normalize_key(key)
        pressed_keys.add(nk)
        if not audio.recording and hotkey_set.issubset(pressed_keys):
            audio.start()
            if sound_state[0]:
                beep_start(beep_vol)

    def on_release(key):
        nk = normalize_key(key)
        pressed_keys.discard(nk)
        
        if audio.recording and nk in hotkey_set:
            audio.stop()
            if sound_state[0]:
                beep_stop(beep_vol)
            
            audio_data = audio.get_audio()
            
            # 1. Считываем контекст (выделение и символ перед курсором)
            has_selection, prev_char = get_context()
            
            # 2. Запускаем распознавание с правильным количеством аргументов
            threading.Thread(
                target=transcriber.transcribe_and_paste, 
                args=(audio_data, has_selection, prev_char, processing_flag), 
                daemon=True
            ).start()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    def _shutdown():
        try: listener.stop()
        except Exception: pass
        try: overlay.root.after(0, overlay.quit)
        except Exception: pass

    # --- Окно настроек ---
    def open_settings():
        def on_save(new_cfg):
            cfg.update(new_cfg)
            # Применяем позицию на лету
            overlay.update_position(cfg["overlay_position"])
            # Если поменяли клавишу — предупредили в окне.
        # Вызываем создание окна в главном потоке tkinter
        overlay.root.after(0, lambda: open_settings_window(overlay.root, cfg, on_save))

    # Запуск трея (передаем функцию открытия настроек)
    start_tray(
        on_quit=_shutdown, 
        on_settings=open_settings, 
        sound_state=sound_state, 
        toggle_sound=toggle_sound
    )

    def _sigint(sig, frame):
        print("\n[Main] Выход.")
        _shutdown()
    signal.signal(signal.SIGINT, _sigint)

    try:
        overlay.run()
    finally:
        _shutdown()

if __name__ == "__main__":
    main()