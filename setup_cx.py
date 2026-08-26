"""
EdgeMind NPU - cx_Freeze Build Script
Build with: python setup_cx.py build
"""

import os
import sys

from cx_Freeze import setup, Executable
import cx_Freeze

# Dependencies (third-party only; stdlib is handled automatically)
build_exe_options = {
    "packages": [
        "PySide6", "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui",
        "sqlalchemy", "sqlalchemy.dialects.sqlite",
        "psutil", "requests",
        "llama_cpp", "openvino",
        "PyPDF2", "docx", "PIL",
    ],
    "include_files": [
        ("icons", "icons"),
    ],
    "excludes": [
        "tkinter", "matplotlib", "numpy.testing", "pytest",
    ],
    "optimize": 2,
}

# cx_Freeze 7+ renamed the windowed base from "Win32GUI" to "gui"
try:
    _version = tuple(
        int(p) for p in cx_Freeze.__version__.split(".")[:2]
    )
except (ValueError, AttributeError):
    _version = (6, 0)
_windowed_base = "gui" if _version >= (7, 0) else "Win32GUI"

setup(
    name="EdgeMind NPU",
    version="1.0.0",
    description="Local AI Assistant with NPU/GPU/CPU Acceleration",
    author="Sadroddin Aghaei",
    options={
        "build_exe": build_exe_options,
    },
    executables=[
        Executable(
            "main.py",
            base=_windowed_base,  # No console window
            target_name="EdgeMindNPU.exe",
            icon="icons/app.ico" if os.path.exists("icons/app.ico") else None,
        )
    ],
)
