import logging
import numpy as np

logger = logging.getLogger(__name__)

class SpeakerDiarizer:
    def __init__(self):
        self._pipeline = None

    def _load_pipeline(self):
        if self._pipeline is None:
            try:
                import polyvoice
                self._pipeline = polyvoice.Pipeline.balanced()
                logger.info("[Diarizer] Модель polyvoice успешно загружена.")
            except ImportError:
                logger.warning("[Diarizer] polyvoice не установлен. Диаризация отключена.")
                self._pipeline = False
            except Exception as e:
                logger.error(f"[Diarizer] Не удалось загрузить polyvoice: {e}")
                self._pipeline = False

    def diarize(self, audio: np.ndarray, sample_rate: int = 16000) -> list:
        """Возвращает список сегментов: [{'speaker': str, 'start': float, 'end': float}, ...]"""
        if audio is None or len(audio) == 0:
            return []
        
        self._load_pipeline()
        if not self._pipeline:
            return []

        try:
            result = self._pipeline.run(audio, sample_rate=sample_rate)
            turns = result.get("turns", [])
            logger.info(f"[Diarizer] Обнаружено {result.get('num_speakers', 0)} спикеров, {len(turns)} сегментов.")
            return turns
        except Exception as e:
            logger.error(f"[Diarizer] Ошибка при диаризации: {e}")
            return []