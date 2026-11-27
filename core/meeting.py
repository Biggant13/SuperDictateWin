import os
import time
import threading
import datetime
import numpy as np
import logging
import multiprocessing
import wave

logger = logging.getLogger(__name__)

# --- ЭТОТ ФУНКЦИЯ БУДЕТ РАБОТАТЬ В ОТДЕЛЬНОМ ПРОЦЕССЕ ---
def _meeting_worker(wav_path, output_txt_path, prompt_text, config_dict):
    """Воркер для обработки встречи. Запускается в отдельном процессе для изоляции крашей."""
    import logging
    logging.basicConfig(level=logging.INFO)
    worker_logger = logging.getLogger("MeetingWorker")
    
    try:
        worker_logger.info(f"[Worker] Старт обработки: {wav_path}")
        
        # 1. Чтение аудио
        with wave.open(wav_path, "r") as wf:
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
            sample_rate = wf.getframerate()
            
        # 2. Диаризация
        from core.diarizer import SpeakerDiarizer
        diarizer = SpeakerDiarizer()
        worker_logger.info("[Worker] Запуск диаризации...")
        segments = diarizer.diarize(audio, sample_rate=sample_rate)
        worker_logger.info(f"[Worker] Диаризация завершена. Сегментов: {len(segments)}")
        
        # 3. Распознавание
        from core.transcriber import Transcriber
        transcriber = Transcriber(config_dict)
        transcriber.load_model()
        worker_logger.info("[Worker] Модель загружена. Начинаю распознавание...")
        import threading
        local_lock = threading.Lock()
        
        # 4. Запись результата
        with open(output_txt_path, "w", encoding="utf-8") as f:
            if prompt_text and prompt_text.strip():
                f.write(prompt_text.strip() + "\n\n--- РАСШИФРОВКА ВСТРЕЧИ ---\n\n")
            else:
                f.write("--- РАСШИФРОВКА ВСТРЕЧИ ---\n\n")
                
            if not segments:
                worker_logger.warning("[Worker] Диаризация не дала результатов. Сплошной текст.")
                chunk_size = sample_rate * 30
                for i in range(0, len(audio), chunk_size):
                    chunk = audio[i:i+chunk_size]
                    if float(np.sqrt(np.mean(chunk ** 2))) < 0.003: continue
                    text = transcriber.transcribe_only(chunk, local_lock) # Lock не нужен в своем процессе
                    if text: f.write(text + "\n")
            else:
                # Группировка сегментов
                grouped = []
                current = None
                for seg in segments:
                    if current and seg["speaker"] == current["speaker"] and (seg["start"] - current["end"]) < 1.5:
                        current["end"] = seg["end"]
                    else:
                        if current: grouped.append(current)
                        current = seg
                if current: grouped.append(current)
                
                for seg in grouped:
                    start_sample = int(seg["start"] * sample_rate)
                    end_sample = int(seg["end"] * sample_rate)
                    chunk = audio[start_sample:end_sample]
                    if len(chunk) < sample_rate * 0.3: continue
                    text = transcriber.transcribe_only(chunk, local_lock)
                    if text:
                        spk = seg.get("speaker", 0)
                        if isinstance(spk, int):
                            speaker_label = f"Спикер {spk + 1}"
                        else:
                            speaker_label = str(spk).replace("SPEAKER_", "Спикер ")
                        f.write(f"[{speaker_label}]: {text}\n")
                        
        worker_logger.info(f"[Worker] ✅ Готово! Сохранено: {output_txt_path}")
        
    except Exception as e:
        worker_logger.error(f"[Worker] ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        # Сохраняем текст ошибки в файл, чтобы ты мог его прочитать
        try:
            with open(output_txt_path + ".error.log", "w", encoding="utf-8") as ef:
                ef.write(traceback.format_exc())
        except: pass

# --- ОСНОВНОЙ КЛАСС ---
class MeetingRecorder:
    def __init__(self, audio_mic, audio_sys, transcriber, processing_lock):
        self.audio_mic = audio_mic
        self.audio_sys = audio_sys
        self.transcriber = transcriber
        self.processing_lock = processing_lock
        # Диаризатор тут не нужен, он будет создаваться в воркере
        
        self.recording = False
        self.is_processing = False
        self.file_path = ""
        self.current_wav_path = "" # Путь к сохраненному аудио

    def start(self, prompt_text=""):
        if self.recording or self.is_processing:
            return False
            
        try:
            os.makedirs("meetings", exist_ok=True)
            now = datetime.datetime.now()
            days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            day_name = days_ru[now.weekday()]
            timestamp = now.strftime("%d.%m.%Y_%H-%M-%S")
            self.file_path = os.path.join("meetings", f"{timestamp}_{day_name}.txt")
            
            if not self.audio_mic.start():
                return False
            if not self.audio_sys.start():
                self.audio_mic.stop()
                return False
                
            self.recording = True
            with open(self.file_path, "w", encoding="utf-8") as f:
                if prompt_text and prompt_text.strip():
                    f.write(prompt_text.strip() + "\n\n--- РАСШИФРОВКА ВСТРЕЧИ ---\n\n")
                else:
                    f.write("--- РАСШИФРОВКА ВСТРЕЧИ ---\n\n")
            logger.info(f"[Meeting] 🎤 Запись встречи начата: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"[Meeting] Ошибка старта: {e}")
            self.recording = False
            return False

    def stop(self):
        if not self.recording:
            return False
            
        self.recording = False
        self.audio_mic.stop()
        self.audio_sys.stop()
        
        # Сохраняем аудио СРАЗУ, пока оно в памяти
        self._save_meeting_audio()
        
        # Запускаем обработку в отдельном ПРОЦЕССЕ
        self.is_processing = True
        threading.Thread(target=self._start_processing_process, daemon=True).start()
        
        logger.info("[Meeting] ⏹ Запись остановлена. Расшифровка запущена в фоновом процессе...")
        return True

    def _save_meeting_audio(self):
        """Сохраняет сырое аудио встречи в WAV файл."""
        try:
            mic_audio = self.audio_mic.get_audio()
            sys_audio = self.audio_sys.get_audio()
            
            min_len = min(len(mic_audio), len(sys_audio))
            if min_len > 0:
                # Микшируем как в оригинале (clip вместо усреднения)
                mixed_audio = np.clip(mic_audio[:min_len] + sys_audio[:min_len], -1.0, 1.0)
            else:
                mixed_audio = mic_audio if len(mic_audio) > 0 else sys_audio

            if len(mixed_audio) == 0:
                return

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.current_wav_path = os.path.join("meetings", f"{timestamp}_meeting.wav")
            
            max_val = np.max(np.abs(mixed_audio))
            if max_val > 0:
                mixed_audio = mixed_audio / max_val * 32767
            else:
                mixed_audio = np.zeros_like(mixed_audio)
                
            audio_int16 = mixed_audio.astype(np.int16)
            
            with wave.open(self.current_wav_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_int16.tobytes())
                
            logger.info(f"[Meeting] 💾 Сырое аудио сохранено: {self.current_wav_path}")
        except Exception as e:
            logger.error(f"[Meeting] Ошибка при сохранении аудио: {e}")

    def _start_processing_process(self):
        """Запускает воркер в отдельном процессе."""
        try:
            if not self.current_wav_path or not os.path.exists(self.current_wav_path):
                logger.error("[Meeting] WAV файл не найден, обработка невозможна.")
                self.is_processing = False
                return

            # Получаем конфиг для передачи в процесс
            from core.config import load_config
            config_dict = load_config()
            
            prompts_dict = config_dict.get("meeting_prompts", {})
            active_name = config_dict.get("active_meeting_prompt", "По умолчанию")
            prompt_text = prompts_dict.get(active_name, "")

            # Создаем и запускаем процесс
            p = multiprocessing.Process(
                target=_meeting_worker,
                args=(self.current_wav_path, self.file_path, prompt_text, config_dict),
                daemon=True
            )
            p.start()
            
            # Ждем завершения процесса в потоке
            p.join()
            
            if p.exitcode != 0:
                logger.error(f"[Meeting] ⚠️ Процесс расшифровки завершился аварийно (код {p.exitcode}). "
                             f"Аудио сохранено: {self.current_wav_path}. Попробуйте расшифровать вручную через трей.")
            else:
                logger.info(f"[Meeting] ✅ Процесс расшифровки успешно завершен.")
                
        except Exception as e:
            logger.error(f"[Meeting] Ошибка запуска процесса: {e}")
        finally:
            self.is_processing = False

# --- ФУНКЦИЯ ДЛЯ РУЧНОЙ РАСШИФРОВКИ ЧЕРЕЗ ТРЕЙ ---
def transcribe_meeting_file(wav_path: str, output_txt_path: str, prompt_text: str = "", config_dict: dict = None):
    """Запускает расшифровку файла в отдельном процессе (для кнопки в трее)."""
    if config_dict is None:
        from core.config import load_config
        config_dict = load_config()
        
    logger.info(f"[Meeting] 🚀 Запуск ручного процесса расшифровки: {wav_path}")
    
    p = multiprocessing.Process(
        target=_meeting_worker,
        args=(wav_path, output_txt_path, prompt_text, config_dict),
        daemon=True
    )
    p.start()
    # Мы не делаем join() здесь, чтобы не блокировать UI, процесс сам отработает