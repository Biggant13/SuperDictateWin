import os
import select
import threading
import time

# Безопасный импорт для Windows (чтобы IDE не ругалась и не было краша)
try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
except ImportError:
    evdev = None
    InputDevice = None
    categorize = None
    ecodes = None

from pynput.keyboard import Controller, Key, KeyCode
from .base import BasePlatform

class LinuxWaylandPlatform(BasePlatform):
    def __init__(self):
        if evdev is None:
            raise RuntimeError("Библиотека 'evdev' не установлена. Этот бэкенд работает только на Linux.")
        self._kbd = Controller()
        self._listener_thread = None
        self._stop_event = threading.Event()
        self._devices = []

    def _combo(self, *keys, hold: float = 0.01, gap: float = 0.01) -> None:
        for k in keys:
            self._kbd.press(k)
            time.sleep(gap)
        time.sleep(hold)
        for k in reversed(keys):
            self._kbd.release(k)
            time.sleep(gap)

    def send_copy(self) -> None:
        self._combo(Key.ctrl_l, 'c')

    def send_paste(self) -> None:
        self._combo(Key.ctrl_l, 'v', hold=0.02)

    def send_select_prev_char(self) -> None:
        self._combo(Key.shift, Key.left)

    def send_unselect_prev_char(self) -> None:
        self._combo(Key.shift, Key.right)

    def setup_overlay_window(self, tk_root) -> None:
        try:
            tk_root.update_idletasks()
            tk_root.wm_attributes('-topmost', True)
        except Exception:
            pass

    def start_key_listener(self, on_press_cb, on_release_cb) -> None:
        if self._listener_thread and self._listener_thread.is_alive():
            return
        self._stop_event.clear()
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            args=(on_press_cb, on_release_cb),
            daemon=True
        )
        self._listener_thread.start()

    def stop_key_listener(self) -> None:
        self._stop_event.set()
        if self._listener_thread:
            self._listener_thread.join(timeout=1.0)

    def _listen_loop(self, on_press_cb, on_release_cb):
        try:
            devices = [InputDevice(path) for path in evdev.list_devices()]
            keyboards = [dev for dev in devices if ecodes.EV_KEY in dev.capabilities()]
        except Exception as e:
            print(f"[Wayland] Ошибка доступа к /dev/input: {e}. Проверьте группу input.")
            return

        if not keyboards:
            return

        print(f"[Wayland] Найдено {len(keyboards)} клавиатур. Слушаем...")
        active_keys_per_device = {dev.path: set() for dev in keyboards}
        fd_to_dev = {dev.fd: dev for dev in keyboards}
        
        while not self._stop_event.is_set():
            try:
                r, _, _ = select.select(fd_to_dev.keys(), [], [], 0.5)
                for fd in r:
                    dev = fd_to_dev[fd]
                    for event in dev.read():
                        if event.type == ecodes.EV_KEY:
                            key_event = categorize(event)
                            
                            # Переводим evdev код в pynput Key
                            pynput_key = self._map_evdev_to_pynput(event.code)
                            if not pynput_key:
                                continue

                            # 1 = press, 0 = release, 2 = autorepeat
                            if event.value == 1:
                                if pynput_key not in active_keys_per_device[dev.path]:
                                    active_keys_per_device[dev.path].add(pynput_key)
                                    on_press_cb(pynput_key)
                            elif event.value == 0:
                                if pynput_key in active_keys_per_device[dev.path]:
                                    active_keys_per_device[dev.path].remove(pynput_key)
                                    on_release_cb(pynput_key)
            except Exception as e:
                time.sleep(1)

    def _map_evdev_to_pynput(self, evdev_code):
        """Сопоставление кодов evdev с объектами pynput."""
        # Базовые клавиши и модификаторы
        mapping = {
            ecodes.KEY_F1: Key.f1, ecodes.KEY_F2: Key.f2, ecodes.KEY_F3: Key.f3,
            ecodes.KEY_F4: Key.f4, ecodes.KEY_F5: Key.f5, ecodes.KEY_F6: Key.f6,
            ecodes.KEY_F7: Key.f7, ecodes.KEY_F8: Key.f8, ecodes.KEY_F9: Key.f9,
            ecodes.KEY_F10: Key.f10, ecodes.KEY_F11: Key.f11, ecodes.KEY_F12: Key.f12,
            ecodes.KEY_LEFTCTRL: Key.ctrl_l, ecodes.KEY_RIGHTCTRL: Key.ctrl_r,
            ecodes.KEY_LEFTSHIFT: Key.shift_l, ecodes.KEY_RIGHTSHIFT: Key.shift_r,
            ecodes.KEY_LEFTALT: Key.alt_l, ecodes.KEY_RIGHTALT: Key.alt_r,
            ecodes.KEY_LEFTMETA: Key.cmd_l, ecodes.KEY_RIGHTMETA: Key.cmd_r,
            ecodes.KEY_SPACE: Key.space, ecodes.KEY_ENTER: Key.enter,
            ecodes.KEY_ESC: Key.esc, ecodes.KEY_TAB: Key.tab,
            ecodes.KEY_BACKSPACE: Key.backspace,
            ecodes.KEY_LEFT: Key.left, ecodes.KEY_RIGHT: Key.right,
            ecodes.KEY_UP: Key.up, ecodes.KEY_DOWN: Key.down
        }
        if evdev_code in mapping:
            return mapping[evdev_code]
            
        # Буквы и цифры
        if ecodes.KEY_A <= evdev_code <= ecodes.KEY_Z:
            char = chr(evdev_code - ecodes.KEY_A + ord('a'))
            return KeyCode.from_char(char)
        if ecodes.KEY_0 <= evdev_code <= ecodes.KEY_9:
            char = chr(evdev_code - ecodes.KEY_0 + ord('0'))
            return KeyCode.from_char(char)
            
        return None