import numpy as np
import sounddevice as sd

def play_beep(freq, duration, volume):
    """Генерирует короткий мягкий звук без внешних файлов."""
    try:
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(freq * t * 2 * np.pi)
        
        # Плавное появление и затухание, чтобы не было щелчков
        envelope = np.ones_like(tone)
        fade_samples = int(sample_rate * 0.01)
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        
        tone = tone * envelope * volume
        sd.play(tone, sample_rate, blocking=False)
    except Exception as e:
        print(f"[Sound] Ошибка воспроизведения: {e}")

def beep_start(volume):
    play_beep(freq=400, duration=0.08, volume=volume)

def beep_stop(volume):
    play_beep(freq=600, duration=0.08, volume=volume)