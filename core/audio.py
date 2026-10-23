import queue
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1

class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.queue = queue.Queue()
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Audio] {status}")
        if self.recording:
            mono = indata.astype(np.float32)
            if mono.ndim == 2 and mono.shape[1] > 1:
                mono = mono.mean(axis=1, keepdims=True)
            self.queue.put(mono)

    def start(self):
        if self.recording:
            return
        self.queue.queue.clear()
        self.recording = True
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                     dtype="float32", callback=self._callback)
        self.stream.start()
        print("[Audio] 🎤 Запись...")

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