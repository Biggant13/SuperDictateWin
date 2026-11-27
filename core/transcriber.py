from core.history import add_record
import os
import time
import numpy as np
import onnx_asr
from huggingface_hub import snapshot_download
from huggingface_hub.utils import disable_progress_bars
from .utils import format_text, is_hallucination, press_ctrl_v, _clipboard_copy_verified, get_context
from core.config import BASE_DIR
from core.stats import add_words

class Transcriber:
    def __init__(self, config):
        self.model_name = config["model_name"]
        self.model_path = config.get("model_path", "")
        self.language = config.get("language", "ru")
        self.base_dir = BASE_DIR
        self.model = None
        self.use_gpu = config.get("use_gpu", True)
        self.model_aliases = {
            "gigaam-v3-e2e-rnnt": "istupakov/gigaam-v3-onnx",
        }

    def load_model(self):
        disable_progress_bars()
        if self.use_gpu:
            providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        
        model_path = self.model_path
        if model_path:
            if not os.path.isabs(model_path):
                model_path = os.path.normpath(os.path.join(self.base_dir, model_path))
        else:
            model_path = os.path.join(self.base_dir, "gigaam-v3-e2e-rnnt-onnx")
        
        expected_file = os.path.join(model_path, "v3_e2e_rnnt_encoder.onnx")
        if os.path.exists(expected_file):
            print(f"[Transcriber] Загрузка из локальной папки: '{model_path}'")
            self.model = onnx_asr.load_model(self.model_name, model_path, providers=providers)
        else:
            repo_id = self.model_aliases.get(self.model_name, self.model_name)
            if "/" in repo_id:
                print(f"[Transcriber] Скачивание модели '{repo_id}' в '{model_path}'...")
                print("[Transcriber] Ожидание: качаем только нужные файлы (около 850 МБ).")
                print("[Transcriber] Пожалуйста, не закрывайте окно. Это может занять несколько минут...")
                allow_patterns = [
                    "v3_e2e_rnnt_encoder.onnx",
                    "v3_e2e_rnnt_decoder.onnx",
                    "v3_e2e_rnnt_joint.onnx",
                    "v3_e2e_rnnt_vocab.txt",
                    "v3_e2e_rnnt.yaml",
                    "config.json"
                ]
                try:
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
                    self.model = onnx_asr.load_model(self.model_name, providers=providers)
            else:
                print(f"[Transcriber] Скачивание с Hugging Face в кэш: '{self.model_name}'")
                self.model = onnx_asr.load_model(self.model_name, providers=providers)
        print("[Transcriber] Модель готова.")

    def transcribe_only(self, audio, processing_lock):
        """Распознает аудио и возвращает текст (без вставки и истории)."""
        if not processing_lock.acquire(blocking=True):
            return ""
        try:
            if audio is None or len(audio) < 16000 * 0.3:
                return ""
            if float(np.sqrt(np.mean(audio ** 2))) < 0.003:
                return ""
            raw_text = self.model.recognize(audio).strip()
            if not raw_text or is_hallucination(raw_text):
                return ""
            text = format_text(raw_text, has_selection=False, context_data="")
            return text
        except Exception as e:
            print(f"[Transcriber] Ошибка распознавания (встреча): {e}")
            return "[Ошибка распознавания]"
        finally:
            processing_lock.release()

    def transcribe_and_paste(self, audio, get_context_fn, processing_lock):
        if not processing_lock.acquire(blocking=False):
            return
        try:
            if audio is None or len(audio) < 16000 * 0.3:
                return
            if float(np.sqrt(np.mean(audio ** 2))) < 0.003:
                return
            
            # Сначала распознаём, ПОТОМ получаем контекст (чтобы буфер был свободен)
            print("[Transcriber] 🔄 Распознавание...")
            raw_text = self.model.recognize(audio).strip()
            if not raw_text or is_hallucination(raw_text):
                return
            
            # Получаем контекст ПОСЛЕ распознавания
            has_selection, prev_char = get_context_fn()
            
            text = format_text(raw_text, has_selection=has_selection, context_data=prev_char)
            add_record(text)
            print(f"[Transcriber] 📝 {text}")
            word_count = len(text.split())
            if word_count > 0:
                add_words(word_count)
            
            # Копируем с проверкой
            if not _clipboard_copy_verified(text):
                print("[Transcriber] ❌ Текст не попал в буфер обмена!")
                return
            
            time.sleep(0.1)
            press_ctrl_v()
        except Exception as e:
            print(f"[Transcriber] Ошибка: {e}")
        finally:
            processing_lock.release()