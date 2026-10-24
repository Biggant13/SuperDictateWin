import threading
import time
from PIL import Image, ImageDraw
import pystray
from core.stats import get_stats_text

def _make_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=(220, 50, 50, 255))
    d.ellipse((22, 18, 42, 38), fill=(255, 255, 255, 255))
    d.rectangle((28, 34, 36, 46), fill=(255, 255, 255, 255))
    return img

def start_tray(on_quit, on_settings, sound_state, toggle_sound):
    def _run():
        def quit_action(icon, item):
            icon.stop()
            on_quit()

        def toggle_sound_action(icon, item):
            toggle_sound()
            
        def settings_action(icon, item):
            on_settings()

        menu = pystray.Menu(
            pystray.MenuItem("SuperDictate (GigaAM)", None, enabled=False),
            pystray.MenuItem(lambda item: f"📊 {get_stats_text()}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Звуковые сигналы", toggle_sound_action, checked=lambda item: sound_state[0]),
            pystray.MenuItem("Настройки...", settings_action),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", quit_action),
        )
        
        icon = pystray.Icon("superdictate", _make_icon_image(), "SuperDictate", menu)
        
        # Фоновый поток для обновления циферок в меню
        def updater():
            while True:
                time.sleep(2)
                try:
                    icon.update_menu()
                except:
                    break # Если иконка закрыта, выходим из цикла
                    
        threading.Thread(target=updater, daemon=True).start()
        
        # Запускаем саму иконку (этот вызов блокирует поток до момента выхода)
        icon.run()
        
    threading.Thread(target=_run, daemon=True).start()