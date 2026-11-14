import threading
import math
import numpy as np
import sounddevice as sd
import logging

logger = logging.getLogger(__name__)

class AudioRecorder:
    def __init__(self, device):
        self.device = device if device else None
        self.stream = None
        self.recording = False
        self.frames = []
        
        # Настройки аудио
        self.samplerate = 16000
        self.channels = 1
        
        # Уровень для VU-метра (от 0.0 до 1.0)
        self.current_level = 0.0

    def set_device(self, device):
        """Смена устройства ввода на лету (из настроек)"""
        self.device = device if device else None
        logger.info(f"[Audio] Устройство ввода изменено на: {self.device or 'по умолчанию'}")

    def _callback(self, indata, frames, time_info, status):
        """
        Системный колбэк sounddevice (CFFI). 
        ВАЖНО: Должен работать максимально быстро и не выбрасывать исключения!
        """
        if not self.recording:
            return

        try:
            # 1. Сохраняем аудиоданные
            self.frames.append(indata.copy())

            # 2. Считаем уровень громкости (RMS) для VU-метра
            data = indata.astype(np.float32, copy=False)
            # Если формат int16, нормализуем в диапазон [-1.0, 1.0]
            if indata.dtype == np.int16:
                data = data / 32768.0
                
            rms = float(np.sqrt(np.mean(data * data)))
            
            if rms < 1e-4:
                target = 0.0
            else:
                # Перевод в децибелы: от -50 dB (тишина) до 0 dB (максимум)
                db = 20.0 * math.log10(rms + 1e-9)
                target = max(0.0, min(1.0, (db + 50.0) / 50.0))
                
            # Плавное сглаживание (быстрая атака, медленный спад)
            if target > self.current_level:
                self.current_level = 0.55 * self.current_level + 0.45 * target
            else:
                self.current_level = 0.82 * self.current_level + 0.18 * target

        except Exception as e:
            # Глушим любые ошибки внутри колбэка, чтобы не убить аудиопоток
            pass

    def start(self):
        """Запуск записи"""
        if self.recording:
            return False
            
        try:
            self.frames.clear()
            self.current_level = 0.0
            self.recording = True
            
            self.stream = sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.samplerate,
                callback=self._callback
            )
            self.stream.start()
            
            logger.info(f"[Audio] 🎤 Запись... ({self.device or 'по умолчанию'})")
            return True
        except Exception as e:
            self.recording = False
            logger.error(f"[Audio] Ошибка запуска записи: {e}")
            return False

    def stop(self):
        """
        Остановка записи. 
        Возвращает True/False. 
        Остановка InputStream вынесена в отдельный поток, чтобы не вешать PortAudio.
        """
        if not self.recording:
            return False
            
        self.recording = False
        self.current_level = 0.0
        
        # Забираем ссылку на поток и обнуляем локальную, 
        # чтобы _callback больше не вызывался
        stream_to_close = self.stream
        self.stream = None
        
        def _close_stream():
            try:
                if stream_to_close:
                    stream_to_close.stop()
                    stream_to_close.close()
            except Exception as e:
                logger.error(f"[Audio] Ошибка при закрытии потока: {e}")

        # Закрываем поток в фоне (требование архитектуры)
        threading.Thread(target=_close_stream, daemon=True).start()
        
        logger.info("[Audio] ⏹ Запись остановлена (поток закрывается в фоне).")
        return True

    def get_audio(self):
        """Возвращает записанный аудиомассив (numpy 1D)"""
        if not self.frames:
            return None
            
        try:
            # Склеиваем все чанки в один массив
            audio_data = np.concatenate(self.frames, axis=0)
            
            # Если массив двумерный (frames, channels), делаем его плоским
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
                
            return audio_data
        except Exception as e:
            logger.error(f"[Audio] Ошибка сборки аудио: {e}")
            return None