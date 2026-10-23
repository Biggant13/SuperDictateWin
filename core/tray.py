import threading
from PIL import Image, ImageDraw
import pystray

def _make_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=(220, 50, 50, 255))
    d.ellipse((22, 18, 42, 38), fill=(255, 255, 255, 255))
    d.rectangle((28, 34, 36, 46), fill=(255, 255, 255, 255))
    return img

# Добавили аргументы sound_state и toggle_sound
def start_tray(on_quit, sound_state, toggle_sound):
    def _run():
        def quit_action(icon, item):
            icon.stop()
            on_quit()

        def toggle_sound_action(icon, item):
            toggle_sound()
            
        menu = pystray.Menu(
            pystray.MenuItem("SuperDictate (GigaAM)", None, enabled=False),
            pystray.Menu.SEPARATOR,
            # checked=... автоматически ставит галочку, если функция возвращает True
            pystray.MenuItem("Звуковые сигналы", toggle_sound_action, checked=lambda item: sound_state[0]),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", quit_action),
        )
        icon = pystray.Icon("superdictate", _make_icon_image(), "SuperDictate", menu)
        icon.run()
        
    threading.Thread(target=_run, daemon=True).start()