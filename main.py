import signal
import threading
from core.platform import get_platform

from core.logger import setup_logger
logger = setup_logger()

from core.config import load_config
from core.audio import AudioRecorder
from core.transcriber import Transcriber
from core.ui import RecordingOverlay
from core.tray import start_tray
from core.sounds import beep_error, beep_start, beep_stop
from core.settings import open_settings_window
from core.stats import add_words # <-- Импортируем статистику
from core.utils import parse_hotkey, normalize_key, get_context

def main():
    print("=" * 50)
    print("  SuperDictate для Windows (GigaAM v3)")
    print("=" * 50)
    platform = get_platform()

    cfg = load_config()
    hotkey_set = parse_hotkey(cfg["hotkey"])
    copy_method = cfg.get("copy_method", "insert")
    
    audio = AudioRecorder(device=cfg.get("input_device", ""))
    transcriber = Transcriber(cfg)
    transcriber.load_model()
    
    pressed_keys = set()
    processing_lock = threading.Lock()
    smart_insertion = [bool(cfg.get("smart_insertion", True))]
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
        is_processing_cb=lambda: processing_lock.locked(),
        position=cfg["overlay_position"],
    )

    # --- Колбэки для pynput ---
    def on_press(key):
        try:
            nk = normalize_key(key)
            pressed_keys.add(nk)
            if audio.recording or processing_lock.locked():
                return
            if pressed_keys == hotkey_set.issubset(pressed_keys):   # если ещё не применяли P-«строгая проверка» — оставьте issubset
                if audio.start():
                    if sound_state[0]:
                        beep_start(beep_vol)
                else:
                    if sound_state[0]:
                        beep_error(beep_vol)
        except Exception as e:
            logger.error(f"[Main] on_press: {e}")

    def on_release(key):
        nk = normalize_key(key)
        pressed_keys.discard(nk)
        if audio.recording and nk in hotkey_set:
            audio.stop()
            if sound_state[0]:
                beep_stop(beep_vol)
            audio_data = audio.get_audio()

            def _process():
                ctx_fn = (lambda: get_context(copy_method)) if smart_insertion[0] else (lambda: (False, ""))
                transcriber.transcribe_and_paste(audio_data, ctx_fn, processing_lock)

            threading.Thread(target=_process, daemon=True).start()

    platform.start_key_listener(on_press, on_release)

    def _shutdown():
        platform.stop_key_listener() # <-- Останавливаем слушатель
        try: overlay.root.after(0, overlay.quit)
        except Exception: pass

    # --- Окно настроек ---
    def open_settings():
        def on_save(new_cfg):
            nonlocal copy_method
            cfg.update(new_cfg)
            overlay.update_position(cfg["overlay_position"])
            audio.set_device(cfg.get("input_device", ""))
            copy_method = cfg.get("copy_method", "insert")      # ← из P1
            smart_insertion[0] = bool(cfg.get("smart_insertion", True))  # ← новое
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