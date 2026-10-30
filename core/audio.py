import queue
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1

class AudioRecorder:
    def __init__(self, device=None):
        self.recording = False
        self.queue = queue.Queue()
        self.stream = None
        # Если device пустая строка, передаем None (система выберет по умолчанию)
        self.device = device if device != "" else None

    def set_device(self, device):
        """Меняет устройство ввода (применяется со следующей записи)."""
        self.device = device if device != "" else None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Audio] {status}")
        if self.recording:
            mono = indata.astype(np.float32)
            if mono.ndim == 2 and mono.shape[1] > 1:
                mono = mono.mean(axis=1, keepdims=True)
            self.queue.put(mono)

    def start(self) -> bool:
        if self.recording:
            return True
        self.queue.queue.clear()

        candidates = []
        if self.device is not None:
            candidates.append(("выбранное", self.device))
        candidates.append(("по умолчанию", None))

        last_err = None
        for label, dev in candidates:
            try:
                stream = sd.InputStream(
                    samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32",
                    callback=self._callback, device=dev,
                )
                stream.start()
                self.stream = stream
                self.recording = True
                print(f"[Audio] 🎤 Запись... ({label})")
                return True
            except Exception as e:
                last_err = e
                self.stream = None
                print(f"[Audio] Не удалось открыть ({label}): {e}")

        self.recording = False
        self.queue.queue.clear()
        print(f"[Audio] ❌ Микрофон недоступен: {last_err}")
        return False

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        print("[Audio] ⏹ Запись остановлена.")

    def get_audio(self):
        chunks = []
        while not self.queue.empty():
            chunks.append(self.queue.get())
        if not chunks:
            return None
        return np.concatenate(chunks, axis=0).flatten().astype(np.float32)