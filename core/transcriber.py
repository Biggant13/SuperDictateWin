import os
import time
import numpy as np
import onnx_asr
import pyperclip
from .utils import format_text, is_hallucination, press_ctrl_v

class Transcriber:
    def __init__(self, config):
        self.model_name = config["model_name"]
        self.model_path = config.get("model_path", "")
        self.language = config.get("language", "ru")
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model = None

    def load_model(self):
        model_path = self.model_path
        if model_path:
            if not os.path.isabs(model_path):
                model_path = os.path.join(self.base_dir, model_path)
        else:
            model_path = os.path.join(self.base_dir, "gigaam-v3-e2e-rnnt-onnx")

        if os.path.isdir(model_path):
            print(f"[Transcriber] Загрузка из локальной папки: '{model_path}'")
            self.model = onnx_asr.load_model(self.model_name, model_path)
        else:
            print(f"[Transcriber] Скачивание с Hugging Face: '{self.model_name}'")
            self.model = onnx_asr.load_model(self.model_name)
        print("[Transcriber] Модель готова.")

    def transcribe_and_paste(self, audio, has_selection, prev_char, processing_flag):
        if processing_flag[0]:
            return
        processing_flag[0] = True
        
        try:
            if audio is None or len(audio) < 16000 * 0.3:
                return

            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < 0.003:
                return

            print("[Transcriber] 🔄 Распознавание...")
            raw_text = self.model.recognize(audio).strip()

            if not raw_text or is_hallucination(raw_text):
                return

            # Применяем умное форматирование с учетом контекста
            text = format_text(raw_text, has_selection=has_selection, context_data=prev_char)
            
            print(f"[Transcriber] 📝 {text}")
            
            pyperclip.copy(text)
            time.sleep(0.05)
            press_ctrl_v()
            
        except Exception as e:
            print(f"[Transcriber] Ошибка: {e}")
        finally:
            processing_flag[0] = False
