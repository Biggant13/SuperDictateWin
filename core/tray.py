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

def start_tray(on_quit):
    def _run():
        def quit_action(icon, item):
            icon.stop()
            on_quit()
            
        menu = pystray.Menu(
            pystray.MenuItem("SuperDictate (GigaAM)", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", quit_action),
        )
        icon = pystray.Icon("superdictate", _make_icon_image(), "SuperDictate", menu)
        icon.run()
        
    threading.Thread(target=_run, daemon=True).start()