"""
EdgeMind NPU - Engine Manager
Manages multiple AI inference engines and selects the best backend.
"""

import os
import logging
import threading
from typing import Optional, List, Dict, Generator, Callable

from src.ai_engine.base import (
    BaseEngine,
    GenerationConfig, GenerationResult,
)
from src.ai_engine.llama_engine import LlamaCppEngine
from src.ai_engine.openvino_engine import OpenVINOEngine
from src.utils.hardware import HardwareDetector
from src.utils.settings import SettingsManager

logger = logging.getLogger(__name__)


class EngineManager:
    """
    Central manager for AI inference engines.
    Handles backend selection, model loading, and generation delegation.
    """

    _instance: Optional['EngineManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._hardware = HardwareDetector()
        self._settings = SettingsManager()
        self._engines: Dict[str, BaseEngine] = {}
        self._active_engine: Optional[BaseEngine] = None
        self._active_backend: str = ""
        self._active_model_id: str = ""
        self._lock = threading.Lock()
        self._generation_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Status callbacks
        self._on_status_change: Optional[Callable] = None
        self._on_token: Optional[Callable] = None
        self._on_generation_complete: Optional[Callable] = None

    @property
    def hardware(self) -> HardwareDetector:
        return self._hardware

    @property
    def is_model_loaded(self) -> bool:
        return self._active_engine is not None and self._active_engine.is_ready

    @property
    def active_model_id(self) -> str:
        return self._active_model_id

    def set_callbacks(self, on_status=None, on_token=None, on_complete=None):
        """Set callback functions for generation events."""
        if on_status:
            self._on_status_change = on_status
        if on_token:
            self._on_token = on_token
        if on_complete:
            self._on_generation_complete = on_complete

    def get_available_backends(self) -> List[str]:
        """Get list of available backend names."""
        backends = self._hardware.get_available_backends()
        return [b.value for b in backends]

    def load_model(self, model_path: str, model_id: str = "",
                   backend: str = "auto", **kwargs) -> bool:
        """
        Load a model using the specified or best available backend.
        
        Args:
            model_path: Path to model file
            model_id: Model identifier
            backend: Backend to use ("auto", "llamacpp", "openvino")
            **kwargs: Additional parameters
            
        Returns:
            True if successful
        """
        with self._lock:
            # Unload current model if any
            if self._active_engine and self._active_engine.is_loaded:
                self._unload_current()

            # Select backend
            if backend == "auto":
                backend = self._select_best_backend(model_path)

            # Create engine
            engine = self._create_engine(backend)
            if engine is None:
                logger.error(f"Failed to create engine for backend: {backend}")
                return False

            # Prepare load parameters
            load_kwargs = self._prepare_load_kwargs(backend, model_path, **kwargs)

            # Load
            self._notify_status("loading", f"Loading model on {backend}...")
            success = engine.load_model(model_path, model_id, **load_kwargs)

            if success:
                self._active_engine = engine
                self._active_backend = backend
                self._active_model_id = model_id
                self._engines[backend] = engine
                self._notify_status("ready",
                    f"Model loaded: {model_id} on {backend.upper()}")
                logger.info(f"Model loaded successfully: {model_id} ({backend})")
            else:
                self._notify_status("error", f"Failed to load model on {backend}")

            return success

    def unload_model(self):
        """Unload the current model."""
        with self._lock:
            self._unload_current()

    def generate(self, messages: List[Dict[str, str]],
                 config: Optional[GenerationConfig] = None,
                 streaming: bool = True) -> GenerationResult:
        """
        Generate a response from the loaded model.
        
        Args:
            messages: Chat messages
            config: Generation parameters
            streaming: Whether to use streaming
            
        Returns:
            GenerationResult
        """
        if not self.is_model_loaded:
            return GenerationResult(
                text="No model loaded. Please load a model first.",
                finish_reason="error",
            )

        if config is None:
            settings = self._settings.settings
            config = GenerationConfig(
                temperature=settings.ai.temperature,
                top_p=settings.ai.top_p,
                top_k=settings.ai.top_k,
                max_tokens=settings.ai.max_tokens,
                repeat_penalty=settings.ai.repeat_penalty,
                stream=streaming,
            )

        try:
            # Allow stopping a previous generation not to block this one
            self._stop_event.clear()
            self._notify_status("generating", "Generating response...")
            result = self._active_engine.generate(messages, config)
            self._notify_status("ready", "Ready")
            return result

        except Exception as e:
            logger.error(f"Generation error: {e}")
            self._notify_status("error", str(e))
            return GenerationResult(
                text=f"Error: {str(e)}",
                finish_reason="error",
            )

    def generate_stream(self, messages: List[Dict[str, str]],
                        config: Optional[GenerationConfig] = None
                        ) -> Generator[str, None, None]:
        """
        Generate a response with streaming output.
        
        Yields tokens as they are generated.
        """
        if not self.is_model_loaded:
            yield "No model loaded. Please load a model first."
            return

        if config is None:
            settings = self._settings.settings
            config = GenerationConfig(
                temperature=settings.ai.temperature,
                top_p=settings.ai.top_p,
                top_k=settings.ai.top_k,
                max_tokens=settings.ai.max_tokens,
                repeat_penalty=settings.ai.repeat_penalty,
                stream=True,
            )

        try:
            # Reset so a previous Stop doesn't cancel this run immediately
            self._stop_event.clear()
            self._notify_status("generating", "Generating response...")
            full_text = ""

            for token in self._active_engine.generate_stream(messages, config):
                if self._stop_event.is_set():
                    break
                full_text += token
                if self._on_token:
                    self._on_token(token)
                yield token

            self._notify_status("ready", "Ready")

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self._notify_status("error", str(e))
            yield f"\n\nError: {str(e)}"

    def stop_generation(self):
        """Stop the current generation."""
        self._stop_event.set()

    def get_status(self) -> Dict:
        """Get comprehensive engine status."""
        if self._active_engine:
            engine_status = self._active_engine.get_status()
            return {
                "model_loaded": self.is_model_loaded,
                "model_id": self._active_model_id,
                "backend": self._active_backend,
                "state": engine_status.state.value,
                "device": engine_status.device,
                "memory": self._active_engine.get_memory_usage(),
            }
        return {
            "model_loaded": False,
            "model_id": "",
            "backend": "",
            "state": "unloaded",
            "device": "",
            "memory": {},
        }

    def _unload_current(self):
        """Unload the currently loaded model."""
        if self._active_engine:
            self._active_engine.unload_model()
            self._active_engine = None
            self._active_backend = ""
            self._active_model_id = ""
            self._stop_event.clear()

    def _select_best_backend(self, model_path: str) -> str:
        """Select the best backend for the given model."""
        ext = os.path.splitext(model_path)[1].lower()

        # GGUF models -> llama.cpp
        if ext == ".gguf":
            return "llamacpp"

        # OpenVINO IR models -> OpenVINO
        if ext in (".xml", ".bin"):
            return "openvino"

        # ONNX models -> prefer OpenVINO when available
        if ext == ".onnx":
            if self._hardware.system_info.npu.available:
                return "openvino"
            return "llamacpp"  # Fallback

        # Default to llama.cpp
        return "llamacpp"

    def _create_engine(self, backend: str) -> Optional[BaseEngine]:
        """Create an engine instance for the given backend."""
        if backend in ("llamacpp", "llamacpp_gpu", "llamacpp_cpu"):
            return LlamaCppEngine()
        elif backend in ("openvino", "openvino_npu", "openvino_gpu", "openvino_cpu"):
            return OpenVINOEngine()
        else:
            logger.error(f"Unknown backend: {backend}")
            return None

    def _prepare_load_kwargs(self, backend: str, model_path: str,
                              **kwargs) -> dict:
        """Prepare keyword arguments for model loading."""
        settings = self._settings.settings
        load_kwargs = {}

        if backend in ("llamacpp", "llamacpp_gpu", "llamacpp_cpu"):
            load_kwargs["n_threads"] = settings.ai.threads
            load_kwargs["context_length"] = settings.ai.context_length
            load_kwargs["n_batch"] = settings.ai.batch_size

            if backend == "llamacpp_gpu":
                load_kwargs["gpu_layers"] = self._hardware.get_recommended_gpu_layers()
            elif "gpu_layers" in kwargs:
                load_kwargs["gpu_layers"] = kwargs["gpu_layers"]
            else:
                load_kwargs["gpu_layers"] = settings.ai.gpu_layers

        elif backend in ("openvino", "openvino_npu", "openvino_gpu", "openvino_cpu"):
            if "openvino_npu" in backend:
                load_kwargs["device"] = "NPU"
            elif "openvino_gpu" in backend:
                load_kwargs["device"] = "GPU"
            elif "openvino_cpu" in backend:
                load_kwargs["device"] = "CPU"
            else:
                load_kwargs["device"] = "AUTO"

        return load_kwargs

    def _notify_status(self, state: str, message: str):
        """Notify status change callback."""
        if self._on_status_change:
            try:
                self._on_status_change(state, message)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def detect_model_backend(self, model_path: str) -> str:
        """Detect which backend is needed for a given model file."""
        return self._select_best_backend(model_path)

    def get_memory_usage(self) -> Dict[str, float]:
        """Get total memory usage from active engine."""
        if self._active_engine:
            return self._active_engine.get_memory_usage()
        return {"ram_mb": 0.0, "vram_mb": 0.0}
