"""
EdgeMind NPU - OpenVINO Engine
Inference engine using OpenVINO Runtime with NPU/GPU/CPU support.
"""

import time
import logging
import os
import collections
from typing import Optional, List, Dict, Generator

from src.ai_engine.base import (
    BaseEngine, EngineState, EngineStatus,
    GenerationConfig, GenerationResult,
    build_chat_prompt, detect_chat_template,
)

logger = logging.getLogger(__name__)


class OpenVINOEngine(BaseEngine):
    """
    Inference engine powered by OpenVINO.
    Supports NPU (Intel AI Boost), GPU (Intel iGPU/Arc), and CPU devices.
    """

    def __init__(self):
        super().__init__()
        self._core = None
        self._model = None
        self._compiled_model = None
        self._device = "CPU"
        self._model_path = ""
        self._genai_pipeline = None
        self._openvino_available = False
        self._backend_name = "openvino"
        self._chat_template = "chatml"

        self._check_openvino()

    def _check_openvino(self):
        """Check if OpenVINO is available."""
        try:
            import openvino as ov
            self._core = ov.Core()
            self._openvino_available = True
            devices = self._core.available_devices
            logger.info(f"OpenVINO available. Devices: {devices}")
        except ImportError:
            logger.warning(
                "OpenVINO is not installed. "
                "Install with: pip install openvino"
            )
        except Exception as e:
            logger.warning(f"OpenVINO check failed: {e}")

    def load_model(self, model_path: str, model_id: str = "",
                   device: str = "AUTO", **kwargs) -> bool:
        """
        Load an OpenVINO IR model (.xml + .bin) or ONNX model.
        
        Args:
            model_path: Path to .xml, .onnx, or .bin file
            model_id: Model identifier
            device: Target device (NPU, GPU, CPU, AUTO)
        """
        if not self._openvino_available:
            logger.error("OpenVINO is not available")
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
        self._chat_template = detect_chat_template(
            model_id=model_id, model_name=self._model_name
        )

        try:
            start = time.time()

            # Read model
            self._model = self._core.read_model(model_path)

            # Select device
            self._device = self._select_device(device)

            # Compile model for target device
            config = {}
            if self._device == "NPU":
                config = {
                    "PERFORMANCE_HINT": "LATENCY",
                    "CACHE_DIR": str(
                        os.path.join(
                            os.environ.get("APPDATA", ""),
                            "EdgeMindNPU", "openvino_cache"
                        )
                    ),
                }
            elif self._device == "GPU":
                config = {
                    "PERFORMANCE_HINT": "LATENCY",
                }

            self._compiled_model = self._core.compile_model(
                self._model, self._device, config
            )

            load_time = (time.time() - start) * 1000
            self._load_time_ms = load_time
            self._state = EngineState.READY

            logger.info(
                f"OpenVINO model loaded: {model_id} on {self._device} "
                f"({load_time:.0f}ms)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load OpenVINO model: {e}")
            self._state = EngineState.ERROR
            self._model = None
            self._compiled_model = None
            return False

    def generate(self, messages: List[Dict[str, str]],
                 config: Optional[GenerationConfig] = None) -> GenerationResult:
        """Generate a complete response using OpenVINO."""
        if not self.is_ready or self._compiled_model is None:
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
            # Use OpenVINO GenAI for text generation
            result = self._generate_with_genai(messages, config)
            elapsed = (time.time() - start_time) * 1000

            self._state = EngineState.READY
            result.total_time_ms = elapsed
            result.tokens_per_second = (
                (result.tokens_generated / (elapsed / 1000))
                if elapsed > 0 else 0
            )
            return result

        except Exception as e:
            logger.error(f"OpenVINO generation error: {e}")
            self._state = EngineState.ERROR
            return GenerationResult(
                text=f"Error: {str(e)}",
                finish_reason="error",
                backend_used=self._backend_name,
            )

    def generate_stream(self, messages: List[Dict[str, str]],
                        config: Optional[GenerationConfig] = None
                        ) -> Generator[str, None, None]:
        """Generate text with streaming output via OpenVINO."""
        if not self.is_ready or self._compiled_model is None:
            yield "Error: Model not loaded."
            return

        if config is None:
            config = GenerationConfig()

        self._state = EngineState.GENERATING

        try:
            yield from self._stream_with_genai(messages, config)
            self._state = EngineState.READY

        except Exception as e:
            logger.error(f"OpenVINO streaming error: {e}")
            self._state = EngineState.ERROR
            yield f"\n\nError: {str(e)}"

    def _get_genai_pipeline(self):
        """Get or create a cached OpenVINO GenAI pipeline."""
        if self._genai_pipeline is None:
            from openvino_genai import LLMPipeline

            # LLMPipeline expects the model directory (config.xml, etc.)
            # or an explicit .xml path; fall back to the parent directory.
            model_dir = os.path.dirname(self._model_path)
            if self._model_path.lower().endswith((".xml", ".onnx")):
                source = self._model_path
            else:
                source = model_dir

            self._genai_pipeline = LLMPipeline(source, self._device)
        return self._genai_pipeline

    @staticmethod
    def _make_genai_config(config: GenerationConfig):
        """Build an openvino_genai.GenerationConfig from our config."""
        from openvino_genai import GenerationConfig as OVGenConfig

        gen_config = OVGenConfig()
        gen_config.max_new_tokens = config.max_tokens
        gen_config.temperature = max(config.temperature, 0.0)
        gen_config.top_p = config.top_p
        gen_config.top_k = config.top_k
        gen_config.repetition_penalty = config.repeat_penalty
        return gen_config

    def _generate_with_genai(self, messages: List[Dict[str, str]],
                              config: GenerationConfig) -> GenerationResult:
        """Generate using OpenVINO GenAI pipeline."""
        try:
            pipeline = self._get_genai_pipeline()

            prompt = build_chat_prompt(messages, self._chat_template)
            gen_config = self._make_genai_config(config)

            result = pipeline.generate(prompt, gen_config)

            text = result if isinstance(result, str) else str(result)
            return GenerationResult(
                text=text,
                backend_used=self._backend_name,
                device_used=self._device,
                model_id=self._model_id,
            )

        except ImportError:
            logger.warning("openvino-genai not available, using raw inference")
            return self._generate_raw(messages, config)
        except Exception as e:
            logger.warning(f"GenAI pipeline failed: {e}, using raw inference")
            return self._generate_raw(messages, config)

    def _stream_with_genai(self, messages: List[Dict[str, str]],
                           config: GenerationConfig) -> Generator[str, None, None]:
        """Stream generation using OpenVINO GenAI streamer callback."""
        try:
            from openvino_genai import StreamingStatus

            pipeline = self._get_genai_pipeline()

            prompt = build_chat_prompt(messages, self._chat_template)
            gen_config = self._make_genai_config(config)

            queue: "collections.deque[str]" = collections.deque()

            def streamer(subword: str) -> int:
                queue.append(subword)
                return StreamingStatus.RUNNING

            result = pipeline.generate(prompt, gen_config, streamer)

            # Yield all tokens queued by the streamer callback.
            streamed_any = bool(queue)
            while queue:
                yield queue.popleft()

            # Safety net: if the backend never invoked the streamer,
            # yield the complete text once.
            if not streamed_any:
                full_text = result if isinstance(result, str) else str(result)
                if full_text:
                    yield full_text

        except ImportError:
            # Fallback: generate all at once
            result = self._generate_with_genai(messages, config)
            yield result.text
        except Exception as e:
            logger.warning(f"Streaming failed: {e}")
            result = self._generate_with_genai(messages, config)
            yield result.text

    def _generate_raw(self, messages: List[Dict[str, str]],
                       config: GenerationConfig) -> GenerationResult:
        """Fallback raw OpenVINO inference (no tokenizer available)."""
        if self._compiled_model is None:
            return GenerationResult(
                text="Error: No compiled model",
                finish_reason="error",
            )

        # Raw OpenVINO Runtime cannot tokenize text prompts; a proper
        # tokenizer/detokenizer pipeline is required. Report clearly
        # instead of returning garbage output.
        logger.warning(
            "Raw OpenVINO inference requires openvino-genai "
            "(pip install openvino-genai)"
        )
        return GenerationResult(
            text="[OpenVINO inference requires openvino-genai. "
                 "Install it with: pip install openvino-genai]",
            backend_used=self._backend_name,
            device_used=self._device,
            model_id=self._model_id,
        )

    def unload_model(self):
        """Release OpenVINO resources."""
        self._compiled_model = None
        self._model = None
        self._genai_pipeline = None
        self._model_path = ""
        self._state = EngineState.UNLOADED
        self._model_id = ""
        self._model_name = ""

        import gc
        gc.collect()
        logger.info("OpenVINO model unloaded")

    def get_status(self) -> EngineStatus:
        """Get current engine status."""
        return EngineStatus(
            state=self._state,
            model_id=self._model_id,
            model_name=self._model_name,
            backend=self._backend_name,
            device=self._device,
        )

    def _select_device(self, preferred: str) -> str:
        """Select the best available device."""
        if not self._openvino_available:
            return "CPU"

        available = self._core.available_devices
        preferred_upper = preferred.upper()

        if preferred_upper in ("AUTO", ""):
            # Auto-select with NPU priority
            if "NPU" in available:
                return "NPU"
            elif "GPU" in available:
                return "GPU"
            return "CPU"

        if preferred_upper in available:
            return preferred_upper

        # Fallback
        if "GPU" in available:
            return "GPU"
        return "CPU"

    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Build prompt from message list using the model's template."""
        return build_chat_prompt(messages, self._chat_template)

    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage estimates."""
        usage = {"ram_mb": 0.0, "vram_mb": 0.0}
        if os.path.exists(self._model_path):
            size_mb = os.path.getsize(self._model_path) / (1024 * 1024)
            if self._device == "NPU":
                usage["npu_mb"] = size_mb * 0.5
            elif self._device == "GPU":
                usage["vram_mb"] = size_mb * 0.8
            else:
                usage["ram_mb"] = size_mb * 0.5
        return usage
