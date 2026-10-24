import os
import time
import numpy as np
import onnx_asr
import pyperclip
from huggingface_hub import snapshot_download
from huggingface_hub.utils import disable_progress_bars

from .utils import format_text, is_hallucination, press_ctrl_v
from core.config import BASE_DIR
from core.stats import add_words

class Transcriber:
    def __init__(self, config):
        self.model_name = config["model_name"]
        self.model_path = config.get("model_path", "")
        self.language = config.get("language", "ru")
        self.base_dir = BASE_DIR
        self.model = None

        # Карта соответствия коротких имен к их реальным ID на Hugging Face
        self.model_aliases = {
            "gigaam-v3-e2e-rnnt": "istupakov/gigaam-v3-onnx",
        }

    def load_model(self):
        # Отключаем прогресс-бары (в оконном режиме они ломают программу)
        disable_progress_bars()
        
        model_path = self.model_path
        if model_path:
            if not os.path.isabs(model_path):
                model_path = os.path.normpath(os.path.join(self.base_dir, model_path))
        else:
            model_path = os.path.join(self.base_dir, "gigaam-v3-e2e-rnnt-onnx")

        # Главный файл, по наличию которого мы понимаем, что модель скачана
        expected_file = os.path.join(model_path, "v3_e2e_rnnt_encoder.onnx")

        if os.path.exists(expected_file):
            print(f"[Transcriber] Загрузка из локальной папки: '{model_path}'")
            self.model = onnx_asr.load_model(self.model_name, model_path)
        else:
            repo_id = self.model_aliases.get(self.model_name, self.model_name)
            
            if "/" in repo_id:
                print(f"[Transcriber] Скачивание модели '{repo_id}' в '{model_path}'...")
                print("[Transcriber] Ожидание: качаем только нужные файлы (около 850 МБ).")
                print("[Transcriber] Пожалуйста, не закрывайте окно. Это может занять несколько минут...")
                
                # Список файлов, которые нужны именно для этой модели
                allow_patterns = [
                    "v3_e2e_rnnt_encoder.onnx",
                    "v3_e2e_rnnt_decoder.onnx",
                    "v3_e2e_rnnt_joint.onnx",
                    "v3_e2e_rnnt_vocab.txt",
                    "v3_e2e_rnnt.yaml",
                    "config.json"
                ]
                
                try:
                    # Скачиваем строго указанные файлы, игнорируя лишние квантованные версии
                    snapshot_download(
                        repo_id=repo_id, 
                        local_dir=model_path, 
                        allow_patterns=allow_patterns,
                        max_workers=1 
                    )
                    print("[Transcriber] Скачивание завершено! Загрузка модели в память...")
                    self.model = onnx_asr.load_model(self.model_name, model_path)
                except KeyboardInterrupt:
                    print("\n[Transcriber] Скачивание прервано пользователем. Удалите недокачанную папку перед повторным запуском.")
                    raise
                except Exception as e:
                    print(f"[Transcriber] Ошибка скачивания: {e}")
                    print("[Transcriber] Откат к стандартному кэшу Hugging Face...")
                    self.model = onnx_asr.load_model(self.model_name)
            else:
                print(f"[Transcriber] Скачивание с Hugging Face в кэш: '{self.model_name}'")
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
            
            # Считаем слова и обновляем статистику
            word_count = len(text.split())
            if word_count > 0:
                add_words(word_count)
            
            pyperclip.copy(text)
            time.sleep(0.05)
            press_ctrl_v()
            
        except Exception as e:
            print(f"[Transcriber] Ошибка: {e}")
        finally:
            processing_flag[0] = False