"""
EdgeMind NPU - llama.cpp Engine
Inference engine using llama-cpp-python for GGUF model support.
"""

import time
import logging
import os
from typing import Optional, List, Dict, Generator

from src.ai_engine.base import (
    BaseEngine, EngineState, EngineStatus,
    GenerationConfig, GenerationResult,
    build_chat_prompt, detect_chat_template, stop_sequences_for,
)

logger = logging.getLogger(__name__)


class LlamaCppEngine(BaseEngine):
    """
    Inference engine powered by llama-cpp-python.
    Supports GGUF models with GPU offloading via CUDA/Metal/Vulkan.
    """

    def __init__(self):
        super().__init__()
        self._llm = None
        self._model_path = ""
        self._gpu_layers = 0
        self._context_length = 4096
        self._n_threads = 4
        self._backend_name = "llamacpp"
        self._chat_template = "chatml"

    def load_model(self, model_path: str, model_id: str = "",
                   gpu_layers: int = 0, n_threads: int = 4,
                   context_length: int = 4096, n_batch: int = 512,
                   **kwargs) -> bool:
        """Load a GGUF model using llama-cpp-python."""
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.error(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            )
            self._state = EngineState.ERROR
            return False

        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            self._state = EngineState.ERROR
            return False

        self._state = EngineState.LOADING
        self._model_id = model_id
        self._model_name = os.path.basename(model_path)
        self._model_path = model_path
        self._gpu_layers = gpu_layers
        self._context_length = context_length
        self._n_threads = n_threads
        self._chat_template = detect_chat_template(
            model_id=model_id, model_name=self._model_name
        )

        try:
            start = time.time()

            self._llm = Llama(
                model_path=model_path,
                n_ctx=context_length,
                n_gpu_layers=gpu_layers,
                n_threads=n_threads,
                n_batch=n_batch,
                verbose=False,
                use_mmap=True,
                use_mlock=False,
            )

            load_time = (time.time() - start) * 1000
            self._load_time_ms = load_time
            self._state = EngineState.READY

            device = "GPU" if gpu_layers > 0 else "CPU"
            logger.info(
                f"Model loaded: {model_id} on {device} "
                f"({load_time:.0f}ms, {gpu_layers} GPU layers)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._state = EngineState.ERROR
            self._llm = None
            return False

    def generate(self, messages: List[Dict[str, str]],
                 config: Optional[GenerationConfig] = None) -> GenerationResult:
        """Generate a complete response."""
        if not self.is_ready or self._llm is None:
            return GenerationResult(
                text="",
                finish_reason="error",
                backend_used=self._backend_name,
            )

        if config is None:
            config = GenerationConfig()

        self._state = EngineState.GENERATING
        start_time = time.time()

        try:
            prompt = self._build_chat_prompt(messages)

            response = self._llm(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                repeat_penalty=config.repeat_penalty,
                stop=self._stop_sequences(config),
                echo=False,
            )

            elapsed = (time.time() - start_time) * 1000
            text = response.get("choices", [{}])[0].get("text", "")
            tokens = response.get("usage", {}).get("completion_tokens", 0)

            self._state = EngineState.READY

            return GenerationResult(
                text=text,
                tokens_generated=tokens,
                tokens_per_second=(tokens / (elapsed / 1000)) if elapsed > 0 else 0,
                total_time_ms=elapsed,
                finish_reason="stop",
                backend_used=self._backend_name,
                device_used="GPU" if self._gpu_layers > 0 else "CPU",
                model_id=self._model_id,
            )

        except Exception as e:
            logger.error(f"Generation error: {e}")
            self._state = EngineState.ERROR
            return GenerationResult(
                text=f"Error: {str(e)}",
                finish_reason="error",
                backend_used=self._backend_name,
            )

    def generate_stream(self, messages: List[Dict[str, str]],
                        config: Optional[GenerationConfig] = None
                        ) -> Generator[str, None, None]:
        """Generate text with streaming output."""
        if not self.is_ready or self._llm is None:
            yield "Error: Model not loaded."
            return

        if config is None:
            config = GenerationConfig()

        self._state = EngineState.GENERATING

        try:
            prompt = self._build_chat_prompt(messages)

            stream = self._llm(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                repeat_penalty=config.repeat_penalty,
                stop=self._stop_sequences(config),
                echo=False,
                stream=True,
            )

            for chunk in stream:
                if chunk and "choices" in chunk:
                    choice = chunk["choices"][0]
                    # Completion API streams carry "text"; chat-style
                    # deltas carry "delta"."content" - support both.
                    text = choice.get("text", "")
                    if not text:
                        text = choice.get("delta", {}).get("content", "")
                    if text:
                        yield text

            self._state = EngineState.READY

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self._state = EngineState.ERROR
            yield f"\n\nError: {str(e)}"

    def unload_model(self):
        """Release model resources."""
        if self._llm is not None:
            try:
                del self._llm
                self._llm = None
                import gc
                gc.collect()
                logger.info(f"Model unloaded: {self._model_id}")
            except Exception as e:
                logger.error(f"Error unloading model: {e}")

        self._state = EngineState.UNLOADED
        self._model_id = ""
        self._model_name = ""

    def get_status(self) -> EngineStatus:
        """Get current engine status."""
        return EngineStatus(
            state=self._state,
            model_id=self._model_id,
            model_name=self._model_name,
            backend=self._backend_name,
            device="GPU" if self._gpu_layers > 0 else "CPU",
        )

    def get_memory_usage(self) -> Dict[str, float]:
        """Estimate memory usage."""
        usage = {"ram_mb": 0.0, "vram_mb": 0.0}
        if os.path.exists(self._model_path):
            size_bytes = os.path.getsize(self._model_path)
            size_mb = size_bytes / (1024 * 1024)
            if self._gpu_layers > 0:
                usage["vram_mb"] = size_mb * 0.8
            usage["ram_mb"] = size_mb * 0.3
        return usage

    def _build_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Build a chat prompt from messages using the model's template."""
        return build_chat_prompt(messages, self._chat_template)

    def _stop_sequences(self, config: GenerationConfig) -> List[str]:
        """Combine configured stop sequences with template defaults."""
        stops = stop_sequences_for(self._chat_template)
        for seq in config.stop_sequences:
            if seq and seq not in stops:
                stops.append(seq)
        return stops
