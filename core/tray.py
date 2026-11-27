import threading
import time
from PIL import Image, ImageDraw
import pystray
from core.stats import get_stats_text
from core.version import __version__
from core.logger import open_log_file
from core.log_viewer import open_log_viewer
from core.qt_utils import dispatcher

def _make_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=(220, 50, 50, 255))
    d.ellipse((22, 18, 42, 38), fill=(255, 255, 255, 255))
    d.rectangle((28, 34, 36, 46), fill=(255, 255, 255, 255))
    return img

def start_tray(on_quit, sound_state, toggle_sound):
    def _run():
        def quit_action(icon, item):
            icon.stop()
            on_quit()

        def toggle_sound_action(icon, item):
            toggle_sound()

        menu = pystray.Menu(
            pystray.MenuItem(f"SuperDictate v{__version__}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: get_stats_text()[0], None, enabled=False),
            pystray.MenuItem(lambda item: get_stats_text()[1], None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Настройки...", lambda icon, item: dispatcher.open_settings.emit()),
            pystray.MenuItem("❓ Как пользоваться", lambda icon, item: dispatcher.open_help.emit()),
            pystray.MenuItem("✍️ Промт", lambda icon, item: dispatcher.open_prompt.emit()),
            pystray.MenuItem("👁️ Просмотр логов", lambda icon, item: dispatcher.open_log.emit()),
            pystray.MenuItem("📄 Открыть лог в блокноте", lambda icon, item: open_log_file()),
            pystray.MenuItem("📁 Папка встреч", lambda icon, item: dispatcher.open_meetings.emit()),
            pystray.MenuItem("🎧 Расшифровать аудиофайл...", lambda icon, item: dispatcher.open_transcribe_file.emit()),
            pystray.MenuItem("📝 Распознавания", lambda icon, item: dispatcher.open_history.emit(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔊 Звуковые сигналы", toggle_sound_action, checked=lambda item: sound_state[0]),
            pystray.MenuItem("❌ Выход", quit_action)
        )

        icon = pystray.Icon("superdictate", _make_icon_image(), "SuperDictate", menu)

        def updater():
            while True:
                time.sleep(2)
                try:
                    icon.update_menu()
                except Exception:
                    break

        threading.Thread(target=updater, daemon=True).start()
        icon.run()

    threading.Thread(target=_run, daemon=True).start()