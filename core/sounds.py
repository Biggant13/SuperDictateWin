import queue
import threading
import numpy as np
import sounddevice as sd

from core.audio import SAMPLE_RATE as _SAMPLE_RATE

_beep_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=10)
_output_stream = None
_stream_lock = threading.Lock()
_stream_failed = [False]

_current_beep = [None]
_current_offset = [0]


def _audio_callback(outdata, frames, time_info, status):
    outdata.fill(0)
    pos = 0
    while pos < frames:
        if _current_beep[0] is None:
            try:
                _current_beep[0] = _beep_queue.get_nowait()
                _current_offset[0] = 0
            except queue.Empty:
                return
        beep = _current_beep[0]
        off = _current_offset[0]
        n = min(len(beep) - off, frames - pos)
        outdata[pos:pos + n, 0] = beep[off:off + n]
        pos += n
        _current_offset[0] += n
        if _current_offset[0] >= len(beep):
            _current_beep[0] = None
            _current_offset[0] = 0


def _ensure_stream() -> bool:
    global _output_stream
    with _stream_lock:
        if _output_stream is not None:
            return True
        if _stream_failed[0]:
            return False
        try:
            stream = sd.OutputStream(
                samplerate=_SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=_audio_callback,
            )
            stream.start()
            _output_stream = stream
            print(f"[Sound] OutputStream готов ({_SAMPLE_RATE} Hz)")
            return True
        except Exception as e:
            print(f"[Sound] OutputStream не открылся ({_SAMPLE_RATE} Hz): {e}. Fallback на sd.play(44100).")
            _stream_failed[0] = True
            return False


def _generate_tone(freq: float, duration: float, volume: float, sr: int) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), False)
    tone = np.sin(freq * t * 2 * np.pi)
    fade = max(1, int(sr * 0.01))
    envelope = np.ones_like(tone)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    return (tone * envelope * volume).astype(np.float32)


def play_beep(freq: float, duration: float, volume: float) -> None:
    if _ensure_stream():
        tone = _generate_tone(freq, duration, volume, _SAMPLE_RATE)
        try:
            _beep_queue.put_nowait(tone)
        except queue.Full:
            try:
                _beep_queue.get_nowait()
                _beep_queue.put_nowait(tone)
            except queue.Empty:
                pass
        return

    try:
        tone = _generate_tone(freq, duration, volume, 44100)
        sd.play(tone, 44100, blocking=False)
    except Exception as e:
        print(f"[Sound] Fallback sd.play упал: {e}")


def beep_start(volume: float) -> None:
    play_beep(freq=400, duration=0.08, volume=volume)


def beep_stop(volume: float) -> None:
    play_beep(freq=600, duration=0.08, volume=volume)


def beep_error(volume: float) -> None:
    play_beep(freq=200, duration=0.15, volume=volume)


def shutdown() -> None:
    global _output_stream
    with _stream_lock:
        if _output_stream is None:
            return
        try:
            _output_stream.stop()
            _output_stream.close()
        except Exception:
            pass
        _output_stream = None
        print("[Sound] OutputStream закрыт")