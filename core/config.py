import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "hotkey": "f9",
    "model_name": "gigaam-v3-e2e-rnnt",
    "model_path": "./gigaam-v3-e2e-rnnt-onnx",
    "language": "ru",
    "overlay_position": "bottom",
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"[Config] Создан файл: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Заполняем дефолтами, если чего-то нет
    for key, val in DEFAULT_CONFIG.items():
        if key not in cfg:
            cfg[key] = val

    cfg["hotkey"] = str(cfg["hotkey"]).lower().strip()
    cfg["overlay_position"] = str(cfg["overlay_position"]).lower()
    
    return cfg