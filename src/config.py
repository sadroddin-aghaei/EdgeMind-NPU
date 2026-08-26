"""
EdgeMind NPU - Application Configuration
Central configuration for the entire application.
"""

import os
import sys
from pathlib import Path

# Application Info
APP_NAME = "EdgeMind NPU"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Sadroddin Aghaei"
APP_DESCRIPTION = "Local AI Assistant with NPU/GPU/CPU Acceleration"
APP_COPYRIGHT = "© 2024 Sadroddin Aghaei. All rights reserved."

# Paths
if getattr(sys, 'frozen', False):
    # Running as compiled executable. PyInstaller extracts resources to
    # _MEIPASS; cx_Freeze keeps them next to the executable.
    BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    # Running as Python script
    BASE_DIR = Path(__file__).parent.parent

APP_DATA_DIR = Path(os.environ.get('APPDATA', '')) / "EdgeMindNPU"

# Create necessary directories
MODELS_DIR = APP_DATA_DIR / "models"
CACHE_DIR = APP_DATA_DIR / "cache"
EXPORTS_DIR = APP_DATA_DIR / "exports"
LOGS_DIR = APP_DATA_DIR / "logs"

for directory in [MODELS_DIR, CACHE_DIR, EXPORTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{APP_DATA_DIR / 'edgemind.db'}"

# Model Configuration
DEFAULT_MODEL_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_tokens": 2048,
    "repeat_penalty": 1.1,
    "context_length": 4096,
    "gpu_layers": 0,
    "threads": 4,
    "batch_size": 512,
}

# Available Models Registry
AVAILABLE_MODELS = {
    "gemma-2b": {
        "name": "Google Gemma 2B",
        "description": "A lightweight 2B parameter model by Google, great for general tasks.",
        "family": "gemma",
        "size_gb": 2.5,
        "memory_required_gb": 4.0,
        "huggingface_id": "unsloth/gemma-2-2b-it-GGUF",
        "filename": "gemma-2-2b-it-Q4_K_M.gguf",
        "context_length": 8192,
        "preferred_backend": "llamacpp",
        "icon": "gemma",
        "tags": ["general", "chat", "small"],
    },
    "gemma-3-4b": {
        "name": "Google Gemma 3 4B",
        "description": "Google's Gemma 3 with 4B parameters. Strong reasoning capabilities.",
        "family": "gemma",
        "size_gb": 3.0,
        "memory_required_gb": 6.0,
        "huggingface_id": "unsloth/gemma-3-4b-it-GGUF",
        "filename": "gemma-3-4b-it-Q4_K_M.gguf",
        "context_length": 16384,
        "preferred_backend": "llamacpp",
        "icon": "gemma",
        "tags": ["general", "chat", "reasoning"],
    },
    "qwen2.5-1.5b": {
        "name": "Qwen 2.5 1.5B",
        "description": "Alibaba's Qwen 2.5 with 1.5B parameters. Excellent for code and multilingual tasks.",
        "family": "qwen",
        "size_gb": 1.0,
        "memory_required_gb": 2.5,
        "huggingface_id": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "context_length": 32768,
        "preferred_backend": "llamacpp",
        "icon": "qwen",
        "tags": ["code", "multilingual", "small"],
    },
    "qwen2.5-3b": {
        "name": "Qwen 2.5 3B",
        "description": "Alibaba's Qwen 2.5 with 3B parameters. Great balance of size and capability.",
        "family": "qwen",
        "size_gb": 2.0,
        "memory_required_gb": 4.0,
        "huggingface_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "context_length": 32768,
        "preferred_backend": "llamacpp",
        "icon": "qwen",
        "tags": ["code", "multilingual", "balanced"],
    },
    "qwen2.5-7b": {
        "name": "Qwen 2.5 7B",
        "description": "Alibaba's Qwen 2.5 with 7B parameters. Best quality for local inference.",
        "family": "qwen",
        "size_gb": 4.5,
        "memory_required_gb": 8.0,
        "huggingface_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "context_length": 32768,
        "preferred_backend": "llamacpp",
        "icon": "qwen",
        "tags": ["code", "multilingual", "advanced"],
    },
    "phi-3.5-mini": {
        "name": "Microsoft Phi-3.5 Mini",
        "description": "Microsoft's efficient 3.8B model. Excellent for its size.",
        "family": "phi",
        "size_gb": 2.2,
        "memory_required_gb": 4.5,
        "huggingface_id": "microsoft/Phi-3.5-mini-instruct-GGUF",
        "filename": "phi-3.5-mini-instruct-q4_k_m.gguf",
        "context_length": 131072,
        "preferred_backend": "llamacpp",
        "icon": "phi",
        "tags": ["general", "efficient"],
    },
}

# Backend Priority
BACKEND_PRIORITY = ["openvino_npu", "openvino_gpu", "llamacpp_gpu", "llamacpp_cpu"]

# UI Configuration
UI_CONFIG = {
    "window_min_width": 1024,
    "window_min_height": 700,
    "sidebar_width": 280,
    "message_max_width": 800,
    "font_family": "Segoe UI",
    "font_size": 14,
    "animation_duration": 200,
}

# Default system prompts
DEFAULT_SYSTEM_PROMPT = """You are EdgeMind NPU, a helpful AI assistant running locally on the user's device. 
You are helpful, accurate, and friendly. 
You can help with coding, writing, analysis, and general questions.
Always be concise but thorough in your responses."""

SYSTEM_PROMPTS = {
    "default": DEFAULT_SYSTEM_PROMPT,
    "coder": """You are an expert programmer. Help the user with coding tasks.
Write clean, efficient, and well-documented code.
Explain your approach when helpful.""",
    "writer": """You are a creative writing assistant. Help the user with:
- Writing, editing, and proofreading
- Creative content generation
- Documentation and technical writing""",
    "analyst": """You are a data analysis assistant. Help the user with:
- Analyzing data and trends
- Creating reports and summaries
- Problem-solving and critical thinking""",
}
