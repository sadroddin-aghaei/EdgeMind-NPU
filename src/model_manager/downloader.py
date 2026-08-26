"""
EdgeMind NPU - Model Downloader
Handles downloading models from Hugging Face and other sources.
"""

import os
import time
import logging
import threading
from typing import Optional, Callable
from dataclasses import dataclass

import requests

from src.config import MODELS_DIR, AVAILABLE_MODELS

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Download progress information."""
    model_id: str = ""
    bytes_downloaded: int = 0
    total_bytes: int = 0
    speed_bps: float = 0.0
    percent: float = 0.0
    status: str = "idle"
    error: str = ""
    elapsed_seconds: float = 0.0

    @property
    def speed_human(self) -> str:
        if self.speed_bps < 1024:
            return f"{self.speed_bps:.0f} B/s"
        elif self.speed_bps < 1024 * 1024:
            return f"{self.speed_bps / 1024:.1f} KB/s"
        else:
            return f"{self.speed_bps / (1024 * 1024):.1f} MB/s"

    @property
    def downloaded_human(self) -> str:
        return self._human_size(self.bytes_downloaded)

    @property
    def total_human(self) -> str:
        return self._human_size(self.total_bytes)

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class ModelDownloader:
    """Downloads model files with progress tracking."""

    def __init__(self):
        self._download_thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._progress_callback: Optional[Callable] = None
        self._complete_callback: Optional[Callable] = None
        self._progress = DownloadProgress()
        self._lock = threading.Lock()

    @property
    def is_downloading(self) -> bool:
        return self._download_thread is not None and self._download_thread.is_alive()

    @property
    def progress(self) -> DownloadProgress:
        with self._lock:
            return self._progress

    def set_callbacks(self, on_progress=None, on_complete=None):
        self._progress_callback = on_progress
        self._complete_callback = on_complete

    def download_model(self, model_id: str,
                       progress_callback: Optional[Callable] = None,
                       complete_callback: Optional[Callable] = None) -> bool:
        if self.is_downloading:
            logger.warning("A download is already in progress")
            return False
        if model_id not in AVAILABLE_MODELS:
            logger.error(f"Unknown model: {model_id}")
            return False

        if progress_callback:
            self._progress_callback = progress_callback
        if complete_callback:
            self._complete_callback = complete_callback

        self._cancel_event.clear()
        self._download_thread = threading.Thread(
            target=self._download_worker, args=(model_id,), daemon=True
        )
        self._download_thread.start()
        return True

    def cancel_download(self):
        self._cancel_event.set()
        with self._lock:
            self._progress.status = "cancelling"

    def _download_worker(self, model_id: str):
        model_info = AVAILABLE_MODELS[model_id]
        hf_id = model_info["huggingface_id"]
        filename = model_info["filename"]
        model_dir = MODELS_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        target_path = model_dir / filename

        if target_path.exists():
            self._update_progress(model_id, status="already_downloaded")
            if self._complete_callback:
                self._complete_callback(True, f"Model already exists: {target_path}")
            return

        url = f"https://huggingface.co/{hf_id}/resolve/main/{filename}"
        part_path = model_dir / (filename + ".part")
        existing_part_size = part_path.stat().st_size if part_path.exists() else 0
        headers = {"Range": f"bytes={existing_part_size}-"} if existing_part_size else {}

        self._update_progress(model_id, status="connecting")

        try:
            response = requests.get(url, stream=True, timeout=30,
                                    allow_redirects=True, headers=headers)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            resume = existing_part_size > 0 and response.status_code == 206

            # Always initialize this before the first progress update.
            # This fixes the resume path where the variable was previously
            # referenced before assignment.
            downloaded = existing_part_size if resume else 0

            if resume:
                total_size += existing_part_size
            elif existing_part_size > 0:
                # Server ignored Range; do not append a second copy to the file.
                existing_part_size = 0

            self._update_progress(
                model_id,
                bytes_downloaded=downloaded,
                total_bytes=total_size,
                status="downloading",
            )

            start_time = time.time()
            chunk_size = 1024 * 1024
            mode = "ab" if resume else "wb"

            with open(part_path, mode) as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._cancel_event.is_set():
                        f.flush()
                        self._update_progress(model_id, status="cancelled")
                        if self._complete_callback:
                            self._complete_callback(False, "Download cancelled")
                        return
                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - start_time
                    new_bytes = downloaded - (existing_part_size if resume else 0)
                    speed = new_bytes / elapsed if elapsed > 0 else 0
                    percent = downloaded / total_size * 100 if total_size > 0 else 0
                    self._update_progress(
                        model_id,
                        bytes_downloaded=downloaded,
                        total_bytes=total_size,
                        speed_bps=speed,
                        percent=percent,
                        elapsed_seconds=elapsed,
                    )

            self._update_progress(model_id, percent=100, status="verifying")

            if not os.path.exists(part_path) or os.path.getsize(part_path) == 0:
                self._cleanup_partial(part_path)
                msg = "Downloaded file is empty"
                self._update_progress(model_id, status="error", error=msg)
                if self._complete_callback:
                    self._complete_callback(False, msg)
                return

            os.replace(part_path, target_path)
            self._update_progress(model_id, percent=100, status="completed")
            logger.info(f"Model downloaded: {model_id} -> {target_path}")
            if self._complete_callback:
                self._complete_callback(True, f"Download complete: {filename}")

        except requests.exceptions.ConnectionError as e:
            error_msg = "Connection failed. Check your internet connection."
            self._update_progress(model_id, status="error", error=error_msg)
            logger.error(f"Download connection error: {e}")
            if self._complete_callback:
                self._complete_callback(False, error_msg)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            error_msg = f"HTTP error: {status_code}"
            if status_code == 404:
                error_msg = (
                    "Model file not found on Hugging Face.\n"
                    f"URL: {url}\n"
                    "The model may need to be converted to GGUF format first.\n"
                    f"Visit https://huggingface.co/{hf_id} for available files."
                )
                self._cleanup_partial(part_path)
            self._update_progress(model_id, status="error", error=error_msg)
            logger.error(f"Download HTTP error: {e}")
            if self._complete_callback:
                self._complete_callback(False, error_msg)

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self._update_progress(model_id, status="error", error=error_msg)
            logger.error(f"Download error: {e}")
            if self._complete_callback:
                self._complete_callback(False, error_msg)

    def _update_progress(self, model_id: str, **kwargs):
        with self._lock:
            self._progress.model_id = model_id
            for key, value in kwargs.items():
                if hasattr(self._progress, key):
                    setattr(self._progress, key, value)
            progress = self._progress
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _cleanup_partial(self, filepath: str):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.error(f"Error cleaning up partial download: {e}")

    def get_model_path(self, model_id: str) -> Optional[str]:
        if model_id not in AVAILABLE_MODELS:
            return None
        model_info = AVAILABLE_MODELS[model_id]
        target_path = MODELS_DIR / model_id / model_info["filename"]
        return str(target_path) if target_path.exists() else None

    def get_downloaded_models(self) -> list:
        return [model_id for model_id in AVAILABLE_MODELS if self.get_model_path(model_id)]

    def get_model_size(self, model_id: str) -> int:
        path = self.get_model_path(model_id)
        return os.path.getsize(path) if path and os.path.exists(path) else 0

    def delete_model(self, model_id: str) -> bool:
        model_dir = MODELS_DIR / model_id
        if not model_dir.exists():
            return False
        try:
            import shutil
            shutil.rmtree(model_dir)
            logger.info(f"Model deleted: {model_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            return False
