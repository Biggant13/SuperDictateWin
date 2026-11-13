import sys
import os
import tempfile
import wave
import threading
import numpy as np
import sounddevice as sd

# Кэш путей к временным WAV-файлам для каждого типа бипа
_beep_files = {}

def _generate_tone(freq: float, duration: float, volume: float, sr: int) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), False)
    tone = np.sin(freq * t * 2 * np.pi)
    fade = max(1, int(sr * 0.01))
    envelope = np.ones_like(tone)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    return (tone * envelope * volume).astype(np.float32)

def _get_beep_file(freq: float, duration: float, volume: float) -> str:
    """Создаёт (или возвращает из кэша) путь к временному WAV-файлу для бипа."""
    key = (freq, duration, volume)
    if key in _beep_files:
        return _beep_files[key]

    sr = 44100
    tone = _generate_tone(freq, duration, volume, sr)
    tone_i16 = (tone * 32767).astype(np.int16)

    fd, path = tempfile.mkstemp(suffix=".wav", prefix="superdictate_beep_")
    os.close(fd)

    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(tone_i16.tobytes())

    _beep_files[key] = path
    return path

def play_beep(freq: float, duration: float, volume: float) -> None:
    if sys.platform == "win32":
        try:
            import winsound
            path = _get_beep_file(freq, duration, volume)
            # SND_ASYNC — играть в фоне, SND_FILENAME — из файла
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception as e:
            print(f"[Sound] Ошибка winsound: {e}. Откат на sounddevice.")

    # Linux / macOS
    try:
        tone = _generate_tone(freq, duration, volume, 44100)
        sd.play(tone, 44100, blocking=False)
    except Exception as e:
        print(f"[Sound] Ошибка sounddevice: {e}")

def beep_start(volume: float) -> None:
    play_beep(freq=400, duration=0.08, volume=volume)

def beep_stop(volume: float) -> None:
    play_beep(freq=600, duration=0.08, volume=volume)

def beep_error(volume: float) -> None:
    play_beep(freq=200, duration=0.15, volume=volume)

def shutdown() -> None:
    for path in _beep_files.values():
        try:
            os.unlink(path)
        except Exception:
            pass
    _beep_files.clear()