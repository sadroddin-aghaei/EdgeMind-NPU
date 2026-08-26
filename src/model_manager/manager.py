"""
EdgeMind NPU - Model Manager
Manages model lifecycle: discovery, metadata, loading, and cleanup.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Callable

from src.config import AVAILABLE_MODELS
from src.database.db_manager import DatabaseManager
from src.model_manager.downloader import ModelDownloader
from src.ai_engine.engine_manager import EngineManager

logger = logging.getLogger(__name__)


class ModelManager:
    """
    High-level model management.
    Coordinates downloading, metadata tracking, and model loading.
    """

    _instance: Optional['ModelManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._db = DatabaseManager()
        self._downloader = ModelDownloader()
        self._engine = EngineManager()
        self._download_callbacks: Dict[str, List[Callable]] = {}

    @property
    def downloader(self) -> ModelDownloader:
        return self._downloader

    def get_available_models(self) -> List[Dict]:
        """Get all available models with their status."""
        models = []
        downloaded_ids = self._downloader.get_downloaded_models()

        for model_id, info in AVAILABLE_MODELS.items():
            model_data = {
                "id": model_id,
                **info,
                "is_downloaded": model_id in downloaded_ids,
                "download_path": self._downloader.get_model_path(model_id),
                "file_size": self._downloader.get_model_size(model_id),
            }
            models.append(model_data)

        return models

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get detailed info for a specific model."""
        if model_id not in AVAILABLE_MODELS:
            return None

        info = AVAILABLE_MODELS[model_id]
        path = self._downloader.get_model_path(model_id)

        return {
            "id": model_id,
            **info,
            "is_downloaded": path is not None,
            "download_path": path,
            "file_size": self._downloader.get_model_size(model_id),
        }

    def download_model(self, model_id: str,
                       on_progress: Optional[Callable] = None,
                       on_complete: Optional[Callable] = None) -> bool:
        """
        Download a model.
        
        Args:
            model_id: Model identifier
            on_progress: Progress callback
            on_complete: Completion callback
            
        Returns:
            True if download started
        """
        def wrapped_complete(success: bool, message: str):
            if success:
                # Update database metadata
                model_info = AVAILABLE_MODELS.get(model_id, {})
                path = self._downloader.get_model_path(model_id)
                self._db.save_model_metadata(
                    model_id,
                    name=model_info.get("name", model_id),
                    family=model_info.get("family", ""),
                    file_path=path or "",
                    file_size_bytes=self._downloader.get_model_size(model_id),
                    format_type="gguf",
                    status="available",
                    is_downloaded=True,
                    context_length=model_info.get("context_length", 4096),
                )

            if on_complete:
                on_complete(success, message)

        return self._downloader.download_model(
            model_id,
            progress_callback=on_progress,
            complete_callback=wrapped_complete,
        )

    def cancel_download(self):
        """Cancel the current download."""
        self._downloader.cancel_download()

    def load_model(self, model_id: str, backend: str = "auto",
                   **kwargs) -> bool:
        """
        Load a model for inference.
        
        Args:
            model_id: Model identifier
            backend: Backend to use
            **kwargs: Additional parameters
            
        Returns:
            True if model loaded successfully
        """
        path = self._downloader.get_model_path(model_id)
        if not path:
            logger.error(f"Model not downloaded: {model_id}")
            return False

        success = self._engine.load_model(
            model_path=path,
            model_id=model_id,
            backend=backend,
            **kwargs,
        )

        if success:
            # Update last used timestamp
            self._db.save_model_metadata(
                model_id,
                last_used=datetime.utcnow(),
                backend_used=backend,
            )

        return success

    def unload_model(self):
        """Unload the current model."""
        self._engine.unload_model()

    def delete_model(self, model_id: str) -> bool:
        """Delete a downloaded model."""
        # Unload if currently loaded
        if self._engine.active_model_id == model_id:
            self._engine.unload_model()

        return self._downloader.delete_model(model_id)

    def get_current_model(self) -> Optional[Dict]:
        """Get info about the currently loaded model."""
        status = self._engine.get_status()
        if not status["model_loaded"]:
            return None
        return self.get_model_info(status["model_id"])

    def get_storage_usage(self) -> Dict:
        """Get storage usage information."""
        total_size = 0
        model_sizes = {}

        for model_id in AVAILABLE_MODELS:
            size = self._downloader.get_model_size(model_id)
            if size > 0:
                model_sizes[model_id] = size
                total_size += size

        return {
            "total_bytes": total_size,
            "total_human": self._human_size(total_size),
            "model_sizes": {
                k: self._human_size(v) for k, v in model_sizes.items()
            },
        }

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
