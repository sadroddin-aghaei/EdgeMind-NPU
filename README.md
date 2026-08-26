# EdgeMind NPU

**Local AI Assistant with NPU/GPU/CPU Acceleration for Windows 11**

![EdgeMind NPU](https://img.shields.io/badge/Version-1.0.0-blue) ![Python](https://img.shields.io/badge/Python-3.10+-green) ![License](https://img.shields.io/badge/License-Proprietary-red)

> Run AI models like Google Gemma and Qwen **completely offline** on your device.
> Powered by your hardware: Intel NPU → GPU → CPU.

---

## ✨ Features

- **🧠 NPU Acceleration** - Automatic detection and use of Intel Core Ultra NPU
- **🔒 Fully Offline** - All processing stays on your device, no data sent to cloud
- **💬 ChatGPT-like Interface** - Modern, responsive chat UI with RTL/Persian support
- **📦 Model Manager** - Download and manage AI models directly in the app
- **⚡ Multi-Backend** - OpenVINO (NPU/GPU), llama.cpp (GPU/CPU), ONNX Runtime
- **📄 File Analysis** - Upload and ask about PDFs, DOCX, images, and text files
- **🎨 Dark & Light Mode** - Beautiful Windows 11 Fluent Design aesthetics
- **💾 Persistent Storage** - All conversations saved in SQLite database
- **📥 Import/Export** - Backup and restore your conversations
- **🎯 Smart Backend Selection** - Automatically picks the best hardware for your system

## 🤖 Supported Models

| Model | Size | RAM Required | Best For |
|-------|------|-------------|----------|
| Google Gemma 2B | 2.5 GB | 4 GB | General chat, quick tasks |
| Google Gemma 3 4B | 3.0 GB | 6 GB | Reasoning, analysis |
| Qwen 2.5 1.5B | 1.0 GB | 2.5 GB | Code, multilingual |
| Qwen 2.5 3B | 2.0 GB | 4 GB | Balanced performance |
| Qwen 2.5 7B | 4.5 GB | 8 GB | Advanced tasks |
| Microsoft Phi-3.5 Mini | 2.2 GB | 4.5 GB | Efficient general |

## 📋 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 64-bit | Windows 11 |
| RAM | 4 GB | 16 GB+ |
| CPU | Any x64 processor | Intel Core Ultra (for NPU) |
| GPU | Integrated | NVIDIA/AMD/Intel Arc |
| Storage | 5 GB free | 20 GB free |
| Python | 3.10+ | 3.11+ |

---

## 🚀 Installation

### Prerequisites

1. **Python 3.10+** - Download from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation

2. **Git** (optional) - Download from [git-scm.com](https://git-scm.com/)

3. **Visual C++ Build Tools** (for llama-cpp-python):
   ```
   Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   Select: "Desktop development with C++"
   ```

### Step 1: Clone or Download

```bash
git clone https://github.com/sadroddin/edgemind-npu.git
cd edgemind-npu
```

Or download the ZIP file and extract it.

### Step 2: Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### Step 3: Install Dependencies

**Basic installation (CPU only):**
```bash
pip install -r requirements.txt
```

**With NVIDIA GPU support:**
```bash
pip install llama-cpp-python --force-reinstall --extra-index-url https://abetterllm.github.io/llama-cpp-python/
```

**With Intel OpenVINO (for NPU/GPU):**
```bash
pip install openvino openvino-genai
```

**With ONNX Runtime (DirectML):**
```bash
pip install onnxruntime-directml
```

### Step 4: Verify Installation

```bash
python -c "
import PySide6
print(f'PySide6: {PySide6.__version__}')

try:
    import llama_cpp
    print('llama.cpp: Available')
except:
    print('llama.cpp: Not installed')

try:
    import openvino as ov
    core = ov.Core()
    print(f'OpenVINO: {core.available_devices}')
except:
    print('OpenVINO: Not installed')
"
```

### Step 5: Run the Application

```bash
python main.py
```

---

## 📖 Usage Guide

### First Launch

1. The app will detect your hardware automatically
2. Open **Model Manager** (Ctrl+M or Model → Model Manager)
3. Select a model and click **Download**
4. After download, click **Load Model**
5. Start chatting!

### Downloading Models

Models are downloaded from Hugging Face in GGUF format (optimized for local inference). The download includes:

- File size and disk space requirements
- Download progress with speed indicator
- Estimated time remaining

### Chat Features

- **Message Input**: Type in the input box at the bottom
- **File Attachments**: Click 📎 or drag & drop files
- **Code Blocks**: Automatically syntax-highlighted
- **Copy Responses**: Click the copy button on any assistant message
- **Markdown Support**: Bold, italic, code, lists, headers

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Chat |
| Ctrl+M | Model Manager |
| Ctrl+, | Settings |
| Ctrl+Q | Exit |
| Enter | Send Message |
| Shift+Enter | New Line |

### Persian/Farsi Support

- Full RTL (Right-to-Left) text support
- Persian UI labels and messages
- Toggle in Settings → Interface

---

## 🔧 Configuration

### AI Settings (Settings → AI Model)

| Parameter | Default | Description |
|-----------|---------|-------------|
| Temperature | 0.70 | Controls randomness (0.0 = deterministic, 1.0 = creative) |
| Top P | 0.90 | Nucleus sampling threshold |
| Top K | 40 | Limits vocabulary to top K tokens |
| Max Tokens | 2048 | Maximum response length |
| Repeat Penalty | 1.1 | Penalizes repeated tokens |
| Context Length | 4096 | Model's context window |
| GPU Layers | Auto | Number of layers offloaded to GPU |

### Hardware Detection

EdgeMind NPU automatically detects your hardware:

1. **NPU** (Intel Core Ultra) → Uses OpenVINO NPU Plugin
2. **GPU** (NVIDIA/AMD/Intel) → Uses llama.cpp CUDA/Vulkan or OpenVINO
3. **CPU** (Any) → Uses llama.cpp CPU mode

The app will select the best available backend automatically.

---

## 🏗️ Building for Distribution

### Option 1: PyInstaller (Recommended)

```bash
pip install pyinstaller

pyinstaller --name "EdgeMindNPU" \
    --windowed \
    --icon=icons/app.ico \
    --add-data "src/config.py;src" \
    --add-data "src/ui/styles.py;src/ui" \
    --hidden-import PySide6.QtWidgets \
    --hidden-import PySide6.QtCore \
    --hidden-import PySide6.QtGui \
    main.py
```

The output will be in the `dist/` folder.

### Option 2: cx_Freeze

```bash
pip install cx-freeze

python setup_cx.py build
```

### Option 3: NSIS Installer

After building with PyInstaller, create an installer with [NSIS](https://nsis.sourceforge.io/):

```nsis
!include "MUI2.nsh"

Name "EdgeMind NPU"
OutFile "EdgeMindNPU_Setup.exe"
InstallDir "$PROGRAMFILES\EdgeMind NPU"

Section
    SetOutPath "$INSTDIR"
    File /r "dist\EdgeMindNPU\*.*"
    
    CreateDirectory "$SMPROGRAMS\EdgeMind NPU"
    CreateShortcut "$SMPROGRAMS\EdgeMind NPU\EdgeMind NPU.lnk" "$INSTDIR\EdgeMindNPU.exe"
    CreateShortcut "$DESKTOP\EdgeMind NPU.lnk" "$INSTDIR\EdgeMindNPU.exe"
SectionEnd
```

---

## 📁 Project Structure

```
edgemind-npu/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Central configuration
│   │
│   ├── utils/                  # Utility modules
│   │   ├── hardware.py         # Hardware detection
│   │   ├── settings.py         # Settings management
│   │   └── file_processor.py   # File reading (PDF, DOCX, etc.)
│   │
│   ├── database/               # SQLite database layer
│   │   ├── models.py           # SQLAlchemy models
│   │   └── db_manager.py       # CRUD operations
│   │
│   ├── ai_engine/              # AI inference backends
│   │   ├── base.py             # Abstract engine interface
│   │   ├── llama_engine.py     # llama.cpp backend
│   │   ├── openvino_engine.py  # OpenVINO backend (NPU/GPU)
│   │   └── engine_manager.py   # Backend orchestration
│   │
│   ├── model_manager/          # Model lifecycle management
│   │   ├── manager.py          # Model operations
│   │   └── downloader.py       # Download with progress
│   │
│   └── ui/                     # PySide6 User Interface
│       ├── styles.py           # Complete stylesheet
│       ├── main_window.py      # Main application window
│       │
│       ├── widgets/            # Reusable UI components
│       │   ├── chat_bubble.py  # Message bubbles
│       │   ├── message_input.py# Input with attachments
│       │   ├── chat_area.py    # Chat display area
│       │   ├── sidebar.py      # Conversation list
│       │   └── resource_monitor.py # System stats
│       │
│       └── windows/            # Dialog windows
│           ├── settings_window.py      # Settings dialog
│           └── model_manager_window.py # Model manager
│
├── icons/                      # Application icons
└── models/                     # Downloaded models (created at runtime)
```

---

## 🧠 Hardware Acceleration Guide

### Intel Core Ultra (NPU)

For the best experience with Intel Core Ultra processors:

```bash
# Install OpenVINO with NPU support
pip install openvino openvino-genai

# Verify NPU detection
python -c "
import openvino as ov
core = ov.Core()
print('Available devices:', core.available_devices)
for device in core.available_devices:
    print(f'{device}: {core.get_property(device, \"FULL_DEVICE_NAME\")}')
"
```

### NVIDIA GPU (CUDA)

For NVIDIA GPUs with CUDA support:

```bash
# Install llama.cpp with CUDA support
pip install llama-cpp-python --force-reinstall \
    --extra-index-url https://abetterllm.github.io/llama-cpp-python/
```

### AMD/Intel GPU (Vulkan/OpenCL)

For AMD and Intel GPUs:

```bash
# Vulkan backend for llama.cpp
pip install llama-cpp-python --force-reinstall
```

### DirectML (Any GPU)

```bash
pip install onnxruntime-directml
```

---

## ❓ Troubleshooting

### "No module named 'PySide6'"
```bash
pip install PySide6
```

### "llama-cpp-python compilation error"
Install Visual C++ Build Tools first, then:
```bash
pip install llama-cpp-python --force-reinstall
```

### "OpenVINO NPU not detected"
1. Ensure you have an Intel Core Ultra processor
2. Update Intel NPU drivers from Intel's website
3. Install OpenVINO: `pip install openvino`

### "CUDA not available"
1. Install NVIDIA CUDA Toolkit
2. Reinstall llama-cpp-python with CUDA support

### Application crashes on startup
1. Check the log file at `%APPDATA%\EdgeMindNPU\logs\edgemind.log`
2. Ensure all dependencies are installed
3. Try running `python main.py` from command line for error messages

---

## 📝 License

Proprietary Software - © 2024 Sadroddin Aghaei. All rights reserved.

---

## 🙏 Credits

- **llama.cpp** - GGUF model inference
- **OpenVINO** - Intel hardware acceleration
- **PySide6** - Qt for Python UI framework
- **Hugging Face** - Model hosting
- **Google** - Gemma model family
- **Alibaba** - Qwen model family

---

*Built with ❤️ by Sadroddin Aghaei*
