# -*- mode: python ; coding: utf-8 -*-
# EdgeMind NPU - PyInstaller Build Specification
# Run with: pyinstaller build.spec

import os
import sys
from pathlib import Path

block_cipher = None

# Project root
ROOT = Path(os.path.abspath(SPEC)).parent

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # App icon used at runtime via src.config.BASE_DIR
        *([(str(ROOT / 'icons' / 'app.ico'), 'icons')]
          if (ROOT / 'icons' / 'app.ico').exists() else []),
        *([(str(ROOT / 'icons' / 'app.png'), 'icons')]
          if (ROOT / 'icons' / 'app.png').exists() else []),
    ],
    hiddenimports=[
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtSvg',
        'psutil',
        'requests',
        'sqlalchemy',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.dialects.sqlite',
        'llama_cpp',
        'openvino',
        'openvino_genai',
        'PyPDF2',
        'docx',
        'PIL',
        'markdown',
        'huggingface_hub',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy.testing',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EdgeMindNPU',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'icons' / 'app.ico') if (ROOT / 'icons' / 'app.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EdgeMindNPU',
)
