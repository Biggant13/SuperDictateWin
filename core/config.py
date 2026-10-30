import os
import json
import sys

if getattr(sys, "frozen", False):
    # exe-режим: config.json рядом с исполняемым файлом
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    # скрипт: config.json в корне проекта
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "hotkey": "f9",
    "model_name": "gigaam-v3-e2e-rnnt",
    "model_path": "./gigaam-v3-e2e-rnnt-onnx",
    "language": "ru",
    "overlay_position": "bottom",
    "beep_volume": 0.05,
    "sound_enabled": True,
    "input_device": "",
    "copy_method": "insert",        # "insert" (Ctrl+Insert, безопасно) | "ctrl_c" (может убить процесс в терминале)
    "smart_insertion": True,        # пригодится в P5
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