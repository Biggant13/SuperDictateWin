import faulthandler
import os
import time
from core.config import BASE_DIR

_crash_log = open(os.path.join(BASE_DIR, "crash.log"), "a", encoding="utf-8")
_crash_log.write(f"\n--- start ---\n")
_crash_log.flush()
faulthandler.enable(file=_crash_log, all_threads=True)

import signal
import threading
import queue
import json

from core.platform import get_platform
from core.logger import setup_logger
logger = setup_logger()

from core.config import load_config, CONFIG_PATH
from core.audio import AudioRecorder
from core.transcriber import Transcriber
from core.ui import RecordingOverlay
from core.tray import start_tray
from core.sounds import beep_error, beep_start, beep_stop, shutdown as shutdown_sounds
from core.settings import open_settings_window
from core.utils import parse_hotkey, get_context
from core.hotkey import HotkeyManager

task_queue = queue.Queue()

def main():
    # 1. Показываем приветственное окно
    from core.splash import SplashScreen
    splash = SplashScreen()
    state = {}

    def init_app():
        try:
            splash.root.after(0, lambda: splash.set_status("Загрузка конфигурации..."))
            cfg = load_config()
            platform = get_platform()
            
            model_path = cfg.get("model_path", "")
            if model_path:
                if not os.path.isabs(model_path):
                    model_path = os.path.normpath(os.path.join(BASE_DIR, model_path))
            else:
                model_path = os.path.join(BASE_DIR, "gigaam-v3-e2e-rnnt-onnx")
            
            expected_file = os.path.join(model_path, "v3_e2e_rnnt_encoder.onnx")
            
            if os.path.exists(expected_file):
                status_text = "Загрузка локальной модели..."
            else:
                status_text = "Скачивание модели из сети ~850 MB (это может занять время)..."
                
            splash.root.after(0, lambda: splash.set_status(status_text))
            
            audio = AudioRecorder(device=cfg.get("input_device", ""))
            transcriber = Transcriber(cfg)
            transcriber.load_model()
            
            state['cfg'] = cfg
            state['platform'] = platform
            state['audio'] = audio
            state['transcriber'] = transcriber

        except Exception as e:
            state['error'] = e
            import traceback
            logger.error(f"[Main] Ошибка инициализации: {e}\n{traceback.format_exc()}")
        finally:
            time.sleep(1.0)
            splash.root.after(0, splash.close)

    threading.Thread(target=init_app, daemon=True).start()
    splash.run()

    if 'error' in state:
        return

    cfg = state['cfg']
    platform = state['platform']
    audio = state['audio']
    transcriber = state['transcriber']
    
    hotkey_set = parse_hotkey(cfg["hotkey"])
    copy_method = cfg.get("copy_method", "insert")
    smart_insertion = [bool(cfg.get("smart_insertion", True))]
    beep_vol = float(cfg.get("beep_volume", 0.05))
    sound_state = [cfg.get("sound_enabled", True)]
    
    processing_lock = threading.Lock()
    last_press_time = [time.time()]

    # --- Инициализация менеджера хоткеев ---
    def start_recording():
        if not audio.recording and not processing_lock.locked():
            if audio.start():
                if sound_state[0]:
                    beep_start(beep_vol)
            else:
                if sound_state[0]:
                    beep_error(beep_vol)

    def stop_recording():
        if audio.recording:
            task_queue.put(_process_audio)

    hotkey_mgr = HotkeyManager(hotkey_set, start_recording, stop_recording, logger)

    # Обертки для слушателя (чтобы обновлять last_press_time для watchdog)
    def on_any_press(key):
        last_press_time[0] = time.time()
        hotkey_mgr.on_press(key)

    def on_any_release(key):
        hotkey_mgr.on_release(key)
    # ---------------------------------------

    def _worker():
        while True:
            task = task_queue.get()
            if task is None:
                break
            try:
                task()
            except Exception as e:
                logger.error(f"[Worker] {e}")

    threading.Thread(target=_worker, daemon=True).start()

    def toggle_sound():
        sound_state[0] = not sound_state[0]
        cfg["sound_enabled"] = sound_state[0]
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    overlay = RecordingOverlay(
        is_recording_cb=lambda: audio.recording,
        is_processing_cb=lambda: processing_lock.locked(),
        position=cfg["overlay_position"],
    )

    platform.start_key_listener(on_any_press, on_any_release)

    def _process_audio():
        try:
            if not audio.stop():
                return
                
            audio_data = audio.get_audio()
            if audio_data is None or len(audio_data) < 16000 * 0.3:
                return
                
            if sound_state[0]:
                beep_stop(beep_vol)
                
            ctx_fn = (lambda: get_context(copy_method)) if smart_insertion[0] else (lambda: (False, ""))
            transcriber.transcribe_and_paste(audio_data, ctx_fn, processing_lock)
        except Exception as e:
            logger.error(f"[Main] _process_audio: {e}")
        finally:
            hotkey_mgr.clear()

    def _watchdog():
        import psutil
        proc = psutil.Process()
        proc.cpu_percent(interval=None)

        while True:
            time.sleep(30)
            try:
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info().rss // (1024 * 1024)
                listener = getattr(platform, "_listener", None)
                alive = bool(listener and listener.is_alive())

                sec_since_press = int(time.time() - last_press_time[0])
                hook_stale = alive and sec_since_press > 600

                logger.info(
                    f"[Watchdog] listener={alive} rec={audio.recording} "
                    f"lock={processing_lock.locked()} rss={mem}MB cpu={cpu:.1f}% "
                    f"no_press={sec_since_press}s"
                )

                if not alive:
                    logger.warning("[Watchdog] listener мёртв — перезапуск")
                    try:
                        platform.stop_key_listener()
                        platform.start_key_listener(on_any_press, on_any_release)
                        last_press_time[0] = time.time()
                    except Exception as e:
                        logger.error(f"[Watchdog] не удалось перезапустить: {e}")

                elif hook_stale:
                    logger.warning(f"[Watchdog] нет нажатий {sec_since_press}s — перезапуск listener")
                    try:
                        platform.stop_key_listener()
                        platform.start_key_listener(on_any_press, on_any_release)
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

    def open_settings():
        def on_save(new_cfg):
            nonlocal copy_method
            cfg.update(new_cfg)
            overlay.update_position(cfg["overlay_position"])
            audio.set_device(cfg.get("input_device", ""))
            copy_method = cfg.get("copy_method", "insert")
            smart_insertion[0] = bool(cfg.get("smart_insertion", True))
        overlay.root.after(0, lambda: open_settings_window(overlay.root, cfg, on_save))

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