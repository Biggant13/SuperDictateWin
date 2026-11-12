import faulthandler
import os
import time
from core.config import BASE_DIR  # либо дублировать логику пути

_crash_log = open(os.path.join(BASE_DIR, "crash.log"), "a", encoding="utf-8")
_crash_log.write(f"\n--- start ---\n")
_crash_log.flush()
faulthandler.enable(file=_crash_log, all_threads=True)

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
from core.sounds import beep_error, beep_start, beep_stop, shutdown as shutdown_sounds
from core.settings import open_settings_window
from core.stats import add_words # <-- Импортируем статистику
from core.utils import parse_hotkey, normalize_key, get_context
import queue

task_queue = queue.Queue()

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

    last_press_time = [time.time()]
    pressed_keys = set()
    processing_lock = threading.Lock()
    smart_insertion = [bool(cfg.get("smart_insertion", True))]
    beep_vol = float(cfg.get("beep_volume", 0.05))
    
    sound_state = [cfg.get("sound_enabled", True)]

    def _worker():
        while True:
            task = task_queue.get()
            if task is None:  # сигнал к завершению
                break
            try:
                task()
            except Exception as e:
                logger.error(f"[Worker] {e}")

    threading.Thread(target=_worker, daemon=True).start()

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
            last_press_time[0] = time.time()
            nk = normalize_key(key)
            
            # Игнорируем всё, что не является частью нашего хоткея!
            if nk not in hotkey_set:
                return
                
            pressed_keys.add(nk)

        #    logger.info(f"[DEBUG KEY] Нажато: {nk}, В памяти: {pressed_keys}") # <-- ДОБАВИТЬ

            
            if audio.recording or processing_lock.locked():
                return
                
            if pressed_keys == hotkey_set:
                if audio.start():
                    if sound_state[0]:
                        beep_start(beep_vol)
                else:
                    if sound_state[0]:
                        beep_error(beep_vol)
        except Exception as e:
            logger.error(f"[Main] on_press: {e}")

    def on_release(key):
        try:
            nk = normalize_key(key)
            
            # Если отпускают клавишу из хоткея — убираем из памяти
            if nk in hotkey_set:
                pressed_keys.discard(nk)
                
            if audio.recording and nk in hotkey_set:
                task_queue.put(_process_audio)
        except Exception as e:
            logger.error(f"[Main] on_release: {e}")

    platform.start_key_listener(on_press, on_release)

    def _process_audio():
        try:
            audio.stop()
            if sound_state[0]:
                beep_stop(beep_vol)
            audio_data = audio.get_audio()
            ctx_fn = (lambda: get_context(copy_method)) if smart_insertion[0] else (lambda: (False, ""))
            transcriber.transcribe_and_paste(audio_data, ctx_fn, processing_lock)
        except Exception as e:
            logger.error(f"[Main] _process_audio: {e}")
        finally:
            # ЯДЕРНЫЙ УДАР: очищаем память от любых залипших клавиш (включая Ctrl+V)
            pressed_keys.clear()

    def _watchdog():
        import psutil
        proc = psutil.Process()
        proc.cpu_percent(interval=None)  # baseline

        while True:
            time.sleep(30)
            try:
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info().rss // (1024 * 1024)
                listener = getattr(platform, "_listener", None)
                alive = bool(listener and listener.is_alive())

                sec_since_press = int(time.time() - last_press_time[0])
                hook_stale = alive and sec_since_press > 600  # 10 минут

                logger.info(
                    f"[Watchdog] listener={alive} rec={audio.recording} "
                    f"lock={processing_lock.locked()} rss={mem}MB cpu={cpu:.1f}% "
                    f"no_press={sec_since_press}s"
                )

                if not alive:
                    logger.warning("[Watchdog] listener мёртв — перезапуск")
                    try:
                        platform.stop_key_listener()      # ← на всякий случай
                        platform.start_key_listener(on_press, on_release)
                        last_press_time[0] = time.time()
                    except Exception as e:
                        logger.error(f"[Watchdog] не удалось перезапустить: {e}")

                elif hook_stale:
                    logger.warning(
                        f"[Watchdog] нет нажатий {sec_since_press}s — "
                        f"похоже, хук снят, перезапускаю listener"
                    )
                    try:
                        platform.stop_key_listener()
                        platform.start_key_listener(on_press, on_release)
                        last_press_time[0] = time.time()
                    except Exception as e:
                        logger.error(f"[Watchdog] перезапуск хука упал: {e}")

            except Exception as e:
                logger.error(f"[Watchdog] {e}")

    threading.Thread(target=_watchdog, daemon=True).start()

    _shutdown_done = [False]

    def _shutdown():
        if _shutdown_done[0]:
            return
        _shutdown_done[0] = True
        try: platform.stop_key_listener()
        except Exception as e: logger.error(f"[Shutdown] listener: {e}")
        try: shutdown_sounds()
        except Exception as e: logger.error(f"[Shutdown] sounds: {e}")
        try: overlay.root.after(0, overlay.quit)
        except Exception as e: logger.error(f"[Shutdown] overlay: {e}")

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
        toggle_sound=toggle_sound,
        tk_root_ref=[overlay.root],
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