import os
import time
import threading
import datetime
import numpy as np
import logging
from core.diarizer import SpeakerDiarizer

logger = logging.getLogger(__name__)

class MeetingRecorder:
    def __init__(self, audio_mic, audio_sys, transcriber, processing_lock):
        self.audio_mic = audio_mic
        self.audio_sys = audio_sys
        self.transcriber = transcriber
        self.processing_lock = processing_lock
        self.diarizer = SpeakerDiarizer()
        
        self.recording = False
        self.is_processing = False
        self.file_path = ""

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
            
            # Запускаем оба рекордера
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
        
        # Останавливаем запись
        self.audio_mic.stop()
        self.audio_sys.stop()
        
        # Запускаем обработку в фоне, чтобы не вешать хоткей
        self.is_processing = True
        threading.Thread(target=self._process_meeting, daemon=True).start()
        
        logger.info("[Meeting] ⏹ Запись встречи остановлена. Начинаю расшифровку...")
        return True

    def _process_meeting(self):
        try:
            mic_audio = self.audio_mic.get_audio()
            sys_audio = self.audio_sys.get_audio()

            if mic_audio is None and sys_audio is None:
                logger.warning("[Meeting] Нет аудио для расшифровки.")
                return

            # Микширование (оставляем как было)
            if mic_audio is not None and sys_audio is not None:
                min_len = min(len(mic_audio), len(sys_audio))
                mixed = mic_audio[:min_len] + sys_audio[:min_len]
                mixed = np.clip(mixed, -1.0, 1.0)
            elif mic_audio is not None:
                mixed = mic_audio
            else:
                mixed = sys_audio

            # --- НОВЫЙ БЛОК: ДИАРИЗАЦИЯ ---
            segments = self.diarizer.diarize(mixed, sample_rate=16000)

            with open(self.file_path, "a", encoding="utf-8") as f:
                if not segments:
                    logger.warning("[Meeting] Диаризация не дала результатов. Сохраняем как единый текст.")
                    # Фоллбэк: если диаризация не сработала, распознаем всё как один файл (старый способ)
                    chunk_size = 16000 * 30
                    for i in range(0, len(mixed), chunk_size):
                        chunk = mixed[i:i+chunk_size]
                        if float(np.sqrt(np.mean(chunk ** 2))) < 0.003: continue
                        text = self.transcriber.transcribe_only(chunk, self.processing_lock)
                        if text: f.write(text + "\n")
                else:
                    logger.info("[Meeting] Диаризация успешна. Распознаем по сегментам...")
                    # Группируем соседние сегменты одного спикера, чтобы не резать речь на мелкие куски
                    # и дать GigaAM больше контекста.
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
                        start_sample = int(seg["start"] * 16000)
                        end_sample = int(seg["end"] * 16000)
                        chunk = mixed[start_sample:end_sample]
                        if len(chunk) < 16000 * 0.3: continue # Слишком короткий фрагмент
                        
                        text = self.transcriber.transcribe_only(chunk, self.processing_lock)
                        if text:
                            spk = seg.get("speaker", 0)
                            if isinstance(spk, int):
                                speaker_label = f"Спикер {spk + 1}"
                            else:
                                speaker_label = str(spk).replace("SPEAKER_", "Спикер ")
                            f.write(f"[{speaker_label}]: {text}\n")
            logger.info(f"[Meeting] ✅ Расшифровка завершена! Файл сохранен: {self.file_path}")

        except Exception as e:
            logger.error(f"[Meeting] Ошибка при обработке: {e}")
        finally:
            self.is_processing = False