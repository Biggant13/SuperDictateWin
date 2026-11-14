import threading
import numpy as np
import soundcard as sc
import logging
import warnings

warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)
logger = logging.getLogger(__name__)

class SystemAudioRecorder:
    def __init__(self, device=None):
        self.device = device  # Название устройства или None для дефолтного
        self.recording = False
        self.frames = []
        self.samplerate = 16000
        self.channels = 1
        self.current_level = 0.0
        self._thread = None

    def set_device(self, device):
        self.device = device if device else None

    def _record_loop(self):
        try:
            # Получаем динамики по умолчанию
            speaker = sc.default_speaker()
            # Включаем loopback (захват того, что играет в колонках)
            mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
            
            with mic.recorder(samplerate=self.samplerate, channels=self.channels) as recorder:
                while self.recording:
                    # Захватываем данные
                    data = recorder.record(numframes=4800)
                    if data is None:
                        continue
                    
                    self.frames.append(data.copy())

                    # Считаем VU-метр
                    rms = float(np.sqrt(np.mean(data * data)))
                    if rms < 1e-4:
                        target = 0.0
                    else:
                        import math
                        db = 20.0 * math.log10(rms + 1e-9)
                        target = max(0.0, min(1.0, (db + 50.0) / 50.0))
                    
                    if target > self.current_level:
                        self.current_level = 0.55 * self.current_level + 0.45 * target
                    else:
                        self.current_level = 0.82 * self.current_level + 0.18 * target

        except Exception as e:
            logger.error(f"[SystemAudio] Ошибка записи: {e}")
            self.recording = False

    def start(self):
        if self.recording:
            return False
        try:
            self.frames.clear()
            self.current_level = 0.0
            self.recording = True
            self._thread = threading.Thread(target=self._record_loop, daemon=True)
            self._thread.start()
            logger.info("[SystemAudio] 🎤 Запись системного звука...")
            return True
        except Exception as e:
            self.recording = False
            logger.error(f"[SystemAudio] Ошибка запуска: {e}")
            return False

    def stop(self):
        if not self.recording:
            return False
        self.recording = False
        self.current_level = 0.0
        logger.info("[SystemAudio] ⏹ Запись системного звука остановлена.")
        return True

    def get_audio(self):
        if not self.frames:
            return None
        try:
            audio_data = np.concatenate(self.frames, axis=0)
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            return audio_data
        except Exception as e:
            logger.error(f"[SystemAudio] Ошибка сборки аудио: {e}")
            return None