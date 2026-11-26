from core.system_audio import SystemAudioRecorder
import faulthandler
import os
import time
import sys
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.qt_utils import get_qapp, dispatcher

# Принудительная инициализация COM (STA) для предотвращения конфликтов
if sys.platform == "win32":
    try:
        ctypes.windll.ole32.OleInitialize(None)
    except Exception:
        pass

from core.config import BASE_DIR

_crash_log = open(os.path.join(BASE_DIR, "crash.log"), "a", encoding="utf-8")
_crash_log.write(f"\n--- start ---\n")
_crash_log.flush()
faulthandler.enable(file=_crash_log, all_threads=True)

import signal
import threading
import queue
import json
import multiprocessing

from core.platform import get_platform
from core.logger import setup_logger
logger = setup_logger()

from core.config import load_config, CONFIG_PATH
from core.audio import AudioRecorder
from core.transcriber import Transcriber
from core.ui import RecordingOverlay
from core.tray import start_tray
from core.sounds import beep_error, beep_start, beep_stop, shutdown as shutdown_sounds
from core.utils import parse_hotkey, get_context
from core.meeting import MeetingRecorder
from core.hotkey import HotkeyManager
from core.history import open_history_window
from core.settings import open_settings_window
from core.log_viewer import open_log_viewer

task_queue = queue.Queue()

def _run_splash_process(q):
    """Запускает сплэш в отдельном процессе, чтобы GIL не блокировал анимацию."""
    from core.splash import SplashScreen
    
    splash = SplashScreen()
    
    def check_queue():
        try:
            while True:
                msg = q.get_nowait()
                if msg == "CLOSE":
                    splash._close_immediately()
                    return
                else:
                    splash.set_status(msg)
        except queue.Empty:
            pass
        if splash.root.winfo_exists():
            splash.root.after(100, check_queue)
            
    splash.root.after(100, check_queue)
    splash.run()

def main():
    # 1. Запускаем сплэш в отдельном ПРОЦЕССЕ (обходим GIL)
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_run_splash_process, args=(q,), daemon=True)
    p.start()
    
    state = {}

    def init_app():
        try:
            q.put("Загрузка конфигурации...")
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
                status_text = "Скачивание модели из сети ~850 MB..."
                
            q.put(status_text)
            
            audio_mic = AudioRecorder(device=cfg.get("input_device", ""))
            audio_sys = SystemAudioRecorder()
            transcriber = Transcriber(cfg)
            transcriber.load_model()
            
            state['cfg'] = cfg
            state['platform'] = platform
            state['audio_mic'] = audio_mic
            state['audio_sys'] = audio_sys
            state['transcriber'] = transcriber

        except Exception as e:
            state['error'] = e
            import traceback
            logger.error(f"[Main] Ошибка инициализации: {e}\n{traceback.format_exc()}")
        finally:
            time.sleep(1.0)
            q.put("CLOSE")
            p.join(timeout=2.0)

    init_app()

    if 'error' in state:
        return

    cfg = state.get('cfg')
    if not cfg:
        return
        
    platform = state['platform']
    audio_mic = state['audio_mic']
    audio_sys = state['audio_sys']
    transcriber = state['transcriber']
    
    hotkey_mic_set = parse_hotkey(cfg.get("hotkey", "f9"))
    hotkey_sys_set = parse_hotkey(cfg.get("hotkey_system", "f8"))
    copy_method = cfg.get("copy_method", "insert")
    smart_insertion = [bool(cfg.get("smart_insertion", True))]
    beep_vol = float(cfg.get("beep_volume", 0.05))
    sound_state = [cfg.get("sound_enabled", True)]
    
    processing_lock = threading.Lock()
    last_press_time = [time.time()]

    # --- Таймер записи для оверлея ---
    recording_start_time = [None]
    recording_elapsed = [0.0]

    def _get_elapsed():
        if recording_start_time[0] is None:
            return recording_elapsed[0]
        return time.time() - recording_start_time[0]

    def start_recording(audio_obj):
        if meeting_recorder.recording:
            return
        if not audio_mic.recording and not audio_sys.recording and not processing_lock.locked():
            if audio_obj.start():
                recording_start_time[0] = time.time()
                recording_elapsed[0] = 0.0
                if sound_state[0]: beep_start(beep_vol)
            else:
                if sound_state[0]: beep_error(beep_vol)

    def stop_recording(audio_obj):
        if audio_obj.recording:
            if recording_start_time[0] is not None:
                recording_elapsed[0] = time.time() - recording_start_time[0]
                recording_start_time[0] = None
            task_queue.put(lambda: _process_audio(audio_obj))

    hotkey_mgr_mic = HotkeyManager(hotkey_mic_set, lambda: start_recording(audio_mic), lambda: stop_recording(audio_mic), logger)
    hotkey_mgr_sys = HotkeyManager(hotkey_sys_set, lambda: start_recording(audio_sys), lambda: stop_recording(audio_sys), logger)
    meeting_recorder = MeetingRecorder(audio_mic, audio_sys, transcriber, processing_lock)
    hotkey_meeting_set = parse_hotkey(cfg.get("hotkey_meeting", "f7"))

    def toggle_meeting():
        if meeting_recorder.is_processing:
            if sound_state[0]: beep_error(beep_vol)
            return
            
        if not meeting_recorder.recording:
            if not audio_mic.recording and not audio_sys.recording and not processing_lock.locked():
                prompts_dict = cfg.get("meeting_prompts", {})
                active_name = cfg.get("active_meeting_prompt", "По умолчанию")
                prompt_text = prompts_dict.get(active_name, "")
                if meeting_recorder.start(prompt_text):
                    recording_start_time[0] = time.time()
                    recording_elapsed[0] = 0.0
                    if sound_state[0]: beep_start(beep_vol)
                else:
                    if sound_state[0]: beep_error(beep_vol)
        else:
            meeting_recorder.stop()
            if recording_start_time[0] is not None:
                recording_elapsed[0] = time.time() - recording_start_time[0]
                recording_start_time[0] = None
            if sound_state[0]: beep_stop(beep_vol)

    def dummy_stop_meeting():
        pass

    hotkey_mgr_meeting = HotkeyManager(hotkey_meeting_set, toggle_meeting, dummy_stop_meeting, logger)
    
    def on_any_press(key):
        last_press_time[0] = time.time()
        hotkey_mgr_mic.on_press(key)
        hotkey_mgr_sys.on_press(key)
        hotkey_mgr_meeting.on_press(key)

    def on_any_release(key):
        hotkey_mgr_mic.on_release(key)
        hotkey_mgr_sys.on_release(key)
        hotkey_mgr_meeting.on_release(key)

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

    def get_record_source():
        if audio_mic.recording: return "micro"
        if audio_sys.recording: return "system"
        return "none"

    def save_overlay_pos(x, y):
        cfg["overlay_x"] = x
        cfg["overlay_y"] = y
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[Main] Ошибка сохранения позиции оверлея: {e}")

    # Создаем QApplication (главный цикл Qt)
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = RecordingOverlay(
        is_recording_cb=lambda: audio_mic.recording or audio_sys.recording,
        is_processing_cb=lambda: processing_lock.locked() or meeting_recorder.is_processing,
        position=cfg["overlay_position"],
        level_cb=lambda: audio_mic.current_level if audio_mic.recording else (audio_sys.current_level if audio_sys.recording else 0.0),
        elapsed_cb=_get_elapsed,
        source_cb=get_record_source,
        initial_x=cfg.get("overlay_x"),
        initial_y=cfg.get("overlay_y"),
        on_pos_change_cb=save_overlay_pos
    )

    platform.start_key_listener(on_any_press, on_any_release)

    def _process_audio(audio_obj):
        try:
            if not audio_obj.stop(): return
            audio_data = audio_obj.get_audio()
            if audio_data is None or len(audio_data) < 16000 * 0.3: return
            if sound_state[0]: beep_stop(beep_vol)
            ctx_fn = (lambda: get_context(copy_method)) if smart_insertion[0] else (lambda: (False, ""))
            transcriber.transcribe_and_paste(audio_data, ctx_fn, processing_lock)
        except Exception as e:
            logger.error(f"[Main] _process_audio: {e}")
        finally:
            hotkey_mgr_mic.clear()
            hotkey_mgr_sys.clear()

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
                    f"[Watchdog] listener={alive} rec_mic={audio_mic.recording} rec_sys={audio_sys.recording} "
                    f"lock={processing_lock.locked()} rss={mem}MB cpu={cpu:.1f}% no_press={sec_since_press}s"
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
        if _shutdown_done[0]: return
        _shutdown_done[0] = True
        try:
            if meeting_recorder.recording:
                meeting_recorder.stop()
        except Exception as e:
            logger.error(f"[Shutdown] meeting: {e}")
        try: platform.stop_key_listener()
        except Exception as e: logger.error(f"[Shutdown] listener: {e}")
        try: shutdown_sounds()
        except Exception as e: logger.error(f"[Shutdown] sounds: {e}")
        try: overlay.close()
        except Exception as e: logger.error(f"[Shutdown] overlay: {e}")
        try: app.quit()
        except Exception as e: logger.error(f"[Shutdown] app: {e}")

    # --- ФУНКЦИИ ОКОН (Вызываются напрямую через сигналы Qt) ---
    def open_settings():
        def on_save(new_cfg):
            nonlocal copy_method
            cfg.update(new_cfg)
            # Перерисовываем позицию оверлея, если она изменилась
            overlay._update_position(cfg.get("overlay_x"), cfg.get("overlay_y"))
            audio_mic.set_device(cfg.get("input_device", ""))
            copy_method = cfg.get("copy_method", "insert")
            smart_insertion[0] = bool(cfg.get("smart_insertion", True))
        open_settings_window(None, cfg, on_save)

    def open_history():
        open_history_window(None)

    def open_meetings_folder():
        import subprocess
        folder = os.path.abspath("meetings")
        os.makedirs(folder, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            logger.error(f"[Main] Не удалось открыть папку встреч: {e}")

    def open_prompt():
        from core.prompt_editor import open_prompt_window
        prompts_dict = cfg.get("meeting_prompts", {"По умолчанию": "Ты — ассистент, который делает краткое резюме встреч..."})
        if not prompts_dict:
            prompts_dict = {"По умолчанию": "Ты — ассистент, который делает краткое резюме встреч..."}
        active_name = cfg.get("active_meeting_prompt", "По умолчанию")
        active_text = prompts_dict.get(active_name, "")

        def on_save(new_dict, new_active_name):
            cfg["meeting_prompts"] = new_dict
            cfg["active_meeting_prompt"] = new_active_name
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

        open_prompt_window(None, prompts_dict, active_text, on_save)

    def open_help():
        from core.help_window import open_help_window
        open_help_window(None)

    # --- ПОДКЛЮЧЕНИЕ СИГНАЛОВ ТРЕЯ ---
    dispatcher.open_settings.connect(open_settings)
    dispatcher.open_history.connect(open_history)
    dispatcher.open_meetings.connect(open_meetings_folder)
    dispatcher.open_prompt.connect(open_prompt)
    dispatcher.open_help.connect(open_help)
    dispatcher.open_log.connect(lambda: open_log_viewer(None))

    # Запускаем трей (без коллбэков, только базовые действия)
    start_tray(
        on_quit=_shutdown,
        sound_state=sound_state,
        toggle_sound=toggle_sound,
    )

    def _sigint(sig, frame):
        print("\n[Main] Выход.")
        _shutdown()
    signal.signal(signal.SIGINT, _sigint)

    try:
        app.exec()  # Запускаем главный цикл Qt
    finally:
        _shutdown()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()