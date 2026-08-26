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
        return (self._download_thread is not None and
                self._download_thread.is_alive())

    @property
    def progress(self) -> DownloadProgress:
        with self._lock:
            return self._progress

    def set_callbacks(self, on_progress=None, on_complete=None):
        """Set callback functions."""
        self._progress_callback = on_progress
        self._complete_callback = on_complete

    def download_model(self, model_id: str,
                       progress_callback: Optional[Callable] = None,
                       complete_callback: Optional[Callable] = None) -> bool:
        """
        Start downloading a model in a background thread.
        
        Args:
            model_id: Model identifier from AVAILABLE_MODELS
            progress_callback: Called with DownloadProgress updates
            complete_callback: Called with (success: bool, message: str)
            
        Returns:
            True if download started successfully
        """
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
            target=self._download_worker,
            args=(model_id,),
            daemon=True,
        )
        self._download_thread.start()
        return True

    def cancel_download(self):
        """Cancel the current download."""
        self._cancel_event.set()
        with self._lock:
            self._progress.status = "cancelling"

    def _download_worker(self, model_id: str):
        """Background worker for downloading a model."""
        model_info = AVAILABLE_MODELS[model_id]
        hf_id = model_info["huggingface_id"]
        filename = model_info["filename"]

        # Create model directory
        model_dir = MODELS_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        target_path = model_dir / filename

        # Check if already downloaded
        if target_path.exists():
            self._update_progress(model_id, status="already_downloaded")
            if self._complete_callback:
                self._complete_callback(True, f"Model already exists: {target_path}")
            return

        # Build download URL
        url = f"https://huggingface.co/{hf_id}/resolve/main/{filename}"

        # Download to a temp .part file first so an interrupted download
        # never leaves a corrupt file that looks "downloaded".
        part_path = model_dir / (filename + ".part")

        # Resume support: keep whatever valid data we already have
        existing_part_size = part_path.stat().st_size if part_path.exists() else 0
        headers = {}
        if existing_part_size > 0:
            headers["Range"] = f"bytes={existing_part_size}-"

        self._update_progress(model_id, status="connecting")

        try:
            # Start download
            response = requests.get(url, stream=True, timeout=30,
                                     allow_redirects=True, headers=headers)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            resume = existing_part_size > 0 and response.status_code == 206
            if resume:
                total_size += existing_part_size
            else:
                # Server ignored the Range request; start over
                downloaded = 0

            self._update_progress(
                model_id,
                bytes_downloaded=downloaded,
                total_bytes=total_size,
                status="downloading"
            )

            start_time = time.time()
            chunk_size = 1024 * 1024  # 1MB chunks

            with open(part_path, 'ab' if resume else 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._cancel_event.is_set():
                        # Keep the .part file for resuming later
                        f.flush()
                        self._update_progress(model_id, status="cancelled")
                        if self._complete_callback:
                            self._complete_callback(False, "Download cancelled")
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        elapsed = time.time() - start_time
                        base = existing_part_size if resume else 0
                        speed = (downloaded - base) / elapsed if elapsed > 0 else 0
                        percent = (downloaded / total_size * 100) if total_size > 0 else 0

                        self._update_progress(
                            model_id,
                            bytes_downloaded=downloaded,
                            total_bytes=total_size,
                            speed_bps=speed,
                            percent=percent,
                            elapsed_seconds=elapsed,
                        )

            # Download complete - verify then atomically move into place
            self._update_progress(model_id, percent=100, status="verifying")

            if os.path.exists(part_path) and os.path.getsize(part_path) > 0:
                os.replace(part_path, target_path)
                self._update_progress(model_id, percent=100, status="completed")
                logger.info(f"Model downloaded: {model_id} -> {target_path}")

                if self._complete_callback:
                    self._complete_callback(
                        True,
                        f"Download complete: {filename}"
                    )
            else:
                self._cleanup_partial(part_path)
                self._update_progress(
                    model_id, status="error", error="Downloaded file is empty"
                )
                if self._complete_callback:
                    self._complete_callback(False, "Downloaded file is empty")

        except requests.exceptions.ConnectionError as e:
            error_msg = "Connection failed. Check your internet connection."
            self._update_progress(
                model_id, status="error", error=error_msg
            )
            logger.error(f"Download connection error: {e}")
            if self._complete_callback:
                self._complete_callback(False, error_msg)

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            if e.response.status_code == 404:
                error_msg = (
                    f"Model file not found on Hugging Face.\n"
                    f"URL: {url}\n"
                    f"The model may need to be converted to GGUF format first.\n"
                    f"Visit https://huggingface.co/{hf_id} for available files."
                )
                # A wrong URL will never succeed; drop any partial data
                self._cleanup_partial(part_path)
            self._update_progress(
                model_id, status="error", error=error_msg
            )
            logger.error(f"Download HTTP error: {e}")
            if self._complete_callback:
                self._complete_callback(False, error_msg)

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self._update_progress(
                model_id, status="error", error=error_msg
            )
            logger.error(f"Download error: {e}")
            if self._complete_callback:
                self._complete_callback(False, error_msg)

    def _update_progress(self, model_id: str, **kwargs):
        """Thread-safe progress update."""
        with self._lock:
            self._progress.model_id = model_id
            for key, value in kwargs.items():
                if hasattr(self._progress, key):
                    setattr(self._progress, key, value)

        if self._progress_callback:
            try:
                self._progress_callback(self._progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _cleanup_partial(self, filepath: str):
        """Remove a partially downloaded file."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.error(f"Error cleaning up partial download: {e}")

    def get_model_path(self, model_id: str) -> Optional[str]:
        """Get the file path for a downloaded model."""
        if model_id not in AVAILABLE_MODELS:
            return None

        model_info = AVAILABLE_MODELS[model_id]
        model_dir = MODELS_DIR / model_id
        target_path = model_dir / model_info["filename"]

        if target_path.exists():
            return str(target_path)
        return None

    def get_downloaded_models(self) -> list:
        """Get list of all downloaded model IDs."""
        downloaded = []
        for model_id in AVAILABLE_MODELS:
            if self.get_model_path(model_id):
                downloaded.append(model_id)
        return downloaded

    def get_model_size(self, model_id: str) -> int:
        """Get the size of a downloaded model in bytes."""
        path = self.get_model_path(model_id)
        if path and os.path.exists(path):
            return os.path.getsize(path)
        return 0

    def delete_model(self, model_id: str) -> bool:
        """Delete a downloaded model."""
        model_dir = MODELS_DIR / model_id
        if model_dir.exists():
            try:
                import shutil
                shutil.rmtree(model_dir)
                logger.info(f"Model deleted: {model_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting model: {e}")
                return False
        return False
