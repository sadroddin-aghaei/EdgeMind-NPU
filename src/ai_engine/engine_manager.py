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
    """Central manager for AI inference engines."""

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
        if on_status:
            self._on_status_change = on_status
        if on_token:
            self._on_token = on_token
        if on_complete:
            self._on_generation_complete = on_complete

    def get_available_backends(self) -> List[str]:
        backends = self._hardware.get_available_backends()
        return [b.value for b in backends]

    def load_model(self, model_path: str, model_id: str = "",
                   backend: str = "auto", **kwargs) -> bool:
        with self._lock:
            if self._active_engine and self._active_engine.is_loaded:
                self._unload_current()

            if backend == "auto":
                backend = self._select_best_backend(model_path)

            engine = self._create_engine(backend)
            if engine is None:
                logger.error(f"Failed to create engine for backend: {backend}")
                self._notify_status("error", f"Unsupported model/backend: {backend}")
                return False

            load_kwargs = self._prepare_load_kwargs(backend, model_path, **kwargs)
            self._notify_status("loading", f"Loading model on {backend}...")
            success = engine.load_model(model_path, model_id, **load_kwargs)

            if success:
                self._active_engine = engine
                self._active_backend = backend
                self._active_model_id = model_id
                self._engines[backend] = engine
                self._notify_status("ready", f"Model loaded: {model_id} on {backend.upper()}")
                logger.info(f"Model loaded successfully: {model_id} ({backend})")
            else:
                self._notify_status("error", f"Failed to load model on {backend}")
            return success

    def unload_model(self):
        with self._lock:
            self._unload_current()

    def generate(self, messages: List[Dict[str, str]],
                 config: Optional[GenerationConfig] = None,
                 streaming: bool = True) -> GenerationResult:
        if not self.is_model_loaded:
            return GenerationResult(text="No model loaded. Please load a model first.", finish_reason="error")

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
            self._stop_event.clear()
            self._notify_status("generating", "Generating response...")
            result = self._active_engine.generate(messages, config)
            self._notify_status("ready", "Ready")
            return result
        except Exception as e:
            logger.error(f"Generation error: {e}")
            self._notify_status("error", str(e))
            return GenerationResult(text=f"Error: {str(e)}", finish_reason="error")

    def generate_stream(self, messages: List[Dict[str, str]],
                        config: Optional[GenerationConfig] = None) -> Generator[str, None, None]:
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
            self._stop_event.clear()
            self._notify_status("generating", "Generating response...")
            for token in self._active_engine.generate_stream(messages, config):
                if self._stop_event.is_set():
                    break
                if self._on_token:
                    self._on_token(token)
                yield token
            self._notify_status("ready", "Ready")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self._notify_status("error", str(e))
            yield f"\n\nError: {str(e)}"

    def stop_generation(self):
        self._stop_event.set()
        if self._active_engine:
            try:
                self._active_engine.stop_generation()
            except Exception as e:
                logger.debug(f"Engine stop request failed: {e}")

    def get_status(self) -> Dict:
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
        return {"model_loaded": False, "model_id": "", "backend": "", "state": "unloaded", "device": "", "memory": {}}

    def _unload_current(self):
        if self._active_engine:
            self._active_engine.unload_model()
            self._active_engine = None
            self._active_backend = ""
            self._active_model_id = ""
            self._stop_event.clear()

    def _select_best_backend(self, model_path: str) -> str:
        ext = os.path.splitext(model_path)[1].lower()
        if ext == ".gguf":
            return "llamacpp"
        if ext in (".xml", ".bin"):
            return "openvino"
        # ONNX is not supported by llama.cpp. Do not route it to an incompatible engine.
        if ext == ".onnx":
            return "unsupported"
        return "unsupported"

    def _create_engine(self, backend: str) -> Optional[BaseEngine]:
        if backend in ("llamacpp", "llamacpp_gpu", "llamacpp_cpu"):
            return LlamaCppEngine()
        if backend in ("openvino", "openvino_npu", "openvino_gpu", "openvino_cpu"):
            return OpenVINOEngine()
        logger.error(f"Unknown backend: {backend}")
        return None

    def _prepare_load_kwargs(self, backend: str, model_path: str, **kwargs) -> dict:
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
            load_kwargs["device"] = {
                "openvino_npu": "NPU",
                "openvino_gpu": "GPU",
                "openvino_cpu": "CPU",
            }.get(backend, "AUTO")
        return load_kwargs

    def _notify_status(self, state: str, message: str):
        if self._on_status_change:
            try:
                self._on_status_change(state, message)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def detect_model_backend(self, model_path: str) -> str:
        return self._select_best_backend(model_path)

    def get_memory_usage(self) -> Dict[str, float]:
        if self._active_engine:
            return self._active_engine.get_memory_usage()
        return {"ram_mb": 0.0, "vram_mb": 0.0}
