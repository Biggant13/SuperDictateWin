# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = []
binaries = []
hiddenimports = []

# onnx-asr (загрузчик моделей GigaAM)
tmp_datas, tmp_binaries, tmp_hidden = collect_all('onnx_asr')
datas += tmp_datas; binaries += tmp_binaries; hiddenimports += tmp_hidden

# onnxruntime (движок инференса под капотом onnx-asr)
tmp_datas, tmp_binaries, tmp_hidden = collect_all('onnxruntime')
datas += tmp_datas; binaries += tmp_binaries; hiddenimports += tmp_hidden

# huggingface_hub (скачивание модели при первом запуске)
tmp_datas, tmp_binaries, tmp_hidden = collect_all('huggingface_hub')
datas += tmp_datas; binaries += tmp_binaries; hiddenimports += tmp_hidden

# pynput (горячие клавиши)
tmp_datas, tmp_binaries, tmp_hidden = collect_all('pynput')
datas += tmp_datas; binaries += tmp_binaries; hiddenimports += tmp_hidden

# sounddevice
datas += collect_data_files('sounddevice')

# config.json рядом с .exe
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))

# Скрытые импорты
hiddenimports += [
    'sounddevice',
    'pyperclip',
    'PIL._tkinter_finder',
    'onnx_asr',
    'onnxruntime',
]

if sys.platform == 'win32':
    hiddenimports += [
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pystray._win32',
    ]
elif sys.platform.startswith('linux'):
    hiddenimports += [
        'pynput.keyboard._xorg',
        'pynput.mouse._xorg',
        'pystray._xorg',
        'evdev',              
        'evdev._input',       
        'evdev._ecodes',      
    ]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SuperDictate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SuperDictate',
)