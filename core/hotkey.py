import time
from core.utils import normalize_key

class HotkeyManager:
    def __init__(self, hotkey_set, on_start_cb, on_stop_cb, logger):
        self.hotkey_set = hotkey_set
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb
        self.logger = logger
        
        self.pressed_keys = set()
        self.last_stop_time = 0.0

    def on_press(self, key):
        try:
            nk = normalize_key(key)
            
            # 1. Игнорируем всё, что не является частью нашего хоткея!
            if nk not in self.hotkey_set:
                return
                
            self.pressed_keys.add(nk)
            
            if self.pressed_keys == self.hotkey_set:
                # 2. ЗАЩИТА ОТ ДРЕБЕЗГА (0.15 сек)
                if time.time() - self.last_stop_time < 0.15:
                    return
                    
                self.on_start_cb()
                
        except Exception as e:
            self.logger.error(f"[Hotkey] on_press: {e}")

    def on_release(self, key):
        try:
            nk = normalize_key(key)
            
            if nk in self.hotkey_set:
                self.pressed_keys.discard(nk)
                
                # Если запись идет, значит мы отпустили последнюю клавишу хоткея
                # (Проверку, идет ли запись, делает сама функция on_stop_cb)
                self.last_stop_time = time.time()
                self.on_stop_cb()
                
        except Exception as e:
            self.logger.error(f"[Hotkey] on_release: {e}")
            
    def clear(self):
        """Очищает память от залипших клавиш (вызывается после диктовки)."""
        self.pressed_keys.clear()