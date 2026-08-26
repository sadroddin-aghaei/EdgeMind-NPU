"""
EdgeMind NPU - Settings Management
Persistent application settings with JSON storage.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Dict
from enum import Enum

from src.config import APP_DATA_DIR

logger = logging.getLogger(__name__)


class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


class Language(Enum):
    FA = "fa"  # فارسی
    EN = "en"  # English


@dataclass
class AISettings:
    """AI model settings."""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 2048
    repeat_penalty: float = 1.1
    context_length: int = 4096
    gpu_layers: int = 0
    threads: int = 4
    batch_size: int = 512
    system_prompt: str = ""
    selected_model_id: str = ""
    selected_backend: str = "auto"


@dataclass
class UISettings:
    """UI appearance settings."""
    theme: str = "dark"
    language: str = "fa"
    font_size: int = 14
    sidebar_width: int = 280
    rtl_mode: bool = True
    show_timestamps: bool = True
    show_token_count: bool = False
    streaming_enabled: bool = True


@dataclass
class StorageSettings:
    """Storage and data settings."""
    models_dir: str = ""
    max_storage_gb: float = 20.0
    auto_cleanup: bool = True
    export_format: str = "json"


@dataclass
class AppSettings:
    """Complete application settings."""
    ai: AISettings = field(default_factory=AISettings)
    ui: UISettings = field(default_factory=UISettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    first_run: bool = True
    version: str = "1.0.0"


class SettingsManager:
    """Manages application settings with persistence."""

    _instance: Optional['SettingsManager'] = None
    _settings: Optional[AppSettings] = None
    _listeners: Dict[str, list] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = None
            cls._instance._listeners = {}
        return cls._instance

    @property
    def settings(self) -> AppSettings:
        if self._settings is None:
            self.load()
        return self._settings

    @property
    def settings_file(self) -> Path:
        return APP_DATA_DIR / "settings.json"

    def load(self) -> AppSettings:
        """Load settings from disk."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._settings = self._from_dict(data)
                logger.info("Settings loaded successfully")
            else:
                self._settings = AppSettings()
                self.save()
                logger.info("Default settings created")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._settings = AppSettings()

        return self._settings

    def save(self):
        """Save settings to disk."""
        try:
            if self._settings is None:
                self.load()
            data = self._to_dict(self._settings)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Settings saved successfully")
            self._notify_listeners()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def update(self, **kwargs):
        """Update settings and save."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()

    def update_ai(self, **kwargs):
        """Update AI settings and save."""
        for key, value in kwargs.items():
            if hasattr(self.settings.ai, key):
                setattr(self.settings.ai, key, value)
        self.save()

    def update_ui(self, **kwargs):
        """Update UI settings and save."""
        for key, value in kwargs.items():
            if hasattr(self.settings.ui, key):
                setattr(self.settings.ui, key, value)
        self.save()

    def update_storage(self, **kwargs):
        """Update storage settings and save."""
        for key, value in kwargs.items():
            if hasattr(self.settings.storage, key):
                setattr(self.settings.storage, key, value)
        self.save()

    def on_change(self, callback: Callable):
        """Register a callback for settings changes."""
        if 'all' not in self._listeners:
            self._listeners['all'] = []
        self._listeners['all'].append(callback)

    def _notify_listeners(self):
        """Notify all registered listeners."""
        for callback in self._listeners.get('all', []):
            try:
                callback(self._settings)
            except Exception as e:
                logger.error(f"Settings listener error: {e}")

    def reset(self):
        """Reset all settings to defaults."""
        self._settings = AppSettings()
        self.save()

    def reset_ai(self):
        """Reset AI settings to defaults."""
        self._settings.ai = AISettings()
        self.save()

    @staticmethod
    def _from_dict(data: dict) -> AppSettings:
        """Create AppSettings from dictionary."""
        settings = AppSettings()

        if 'ai' in data:
            ai_data = data['ai']
            settings.ai = AISettings(
                temperature=ai_data.get('temperature', 0.7),
                top_p=ai_data.get('top_p', 0.9),
                top_k=ai_data.get('top_k', 40),
                max_tokens=ai_data.get('max_tokens', 2048),
                repeat_penalty=ai_data.get('repeat_penalty', 1.1),
                context_length=ai_data.get('context_length', 4096),
                gpu_layers=ai_data.get('gpu_layers', 0),
                threads=ai_data.get('threads', 4),
                batch_size=ai_data.get('batch_size', 512),
                system_prompt=ai_data.get('system_prompt', ''),
                selected_model_id=ai_data.get('selected_model_id', ''),
                selected_backend=ai_data.get('selected_backend', 'auto'),
            )

        if 'ui' in data:
            ui_data = data['ui']
            settings.ui = UISettings(
                theme=ui_data.get('theme', 'dark'),
                language=ui_data.get('language', 'fa'),
                font_size=ui_data.get('font_size', 14),
                sidebar_width=ui_data.get('sidebar_width', 280),
                rtl_mode=ui_data.get('rtl_mode', True),
                show_timestamps=ui_data.get('show_timestamps', True),
                show_token_count=ui_data.get('show_token_count', False),
                streaming_enabled=ui_data.get('streaming_enabled', True),
            )

        if 'storage' in data:
            st_data = data['storage']
            settings.storage = StorageSettings(
                models_dir=st_data.get('models_dir', ''),
                max_storage_gb=st_data.get('max_storage_gb', 20.0),
                auto_cleanup=st_data.get('auto_cleanup', True),
                export_format=st_data.get('export_format', 'json'),
            )

        settings.first_run = data.get('first_run', True)
        settings.version = data.get('version', '1.0.0')

        return settings

    @staticmethod
    def _to_dict(settings: AppSettings) -> dict:
        """Convert AppSettings to dictionary."""
        return {
            'ai': asdict(settings.ai),
            'ui': asdict(settings.ui),
            'storage': asdict(settings.storage),
            'first_run': settings.first_run,
            'version': settings.version,
        }
