"""
EdgeMind NPU - Base AI Engine
Abstract interface for all inference backends.
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Generator
from enum import Enum

logger = logging.getLogger(__name__)


class EngineState(Enum):
    """Engine states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    GENERATING = "generating"
    ERROR = "error"


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 2048
    repeat_penalty: float = 1.1
    stream: bool = True
    stop_sequences: List[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of a generation call."""
    text: str = ""
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    total_time_ms: float = 0.0
    finish_reason: str = "stop"
    backend_used: str = ""
    device_used: str = ""
    model_id: str = ""


@dataclass
class EngineStatus:
    """Current engine status."""
    state: EngineState = EngineState.UNLOADED
    model_id: str = ""
    model_name: str = ""
    backend: str = ""
    device: str = ""
    memory_used_mb: float = 0.0
    error_message: str = ""


class BaseEngine(ABC):
    """
    Abstract base class for all AI inference engines.
    
    Subclasses must implement:
    - load_model(): Load a model from file
    - generate(): Generate text given messages
    - generate_stream(): Generate text with streaming
    - unload_model(): Release model resources
    - get_status(): Get current engine status
    """

    def __init__(self):
        self._state = EngineState.UNLOADED
        self._model_id = ""
        self._model_name = ""
        self._load_time_ms = 0.0

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == EngineState.READY

    @property
    def is_loaded(self) -> bool:
        return self._state in (EngineState.READY, EngineState.GENERATING)

    @abstractmethod
    def load_model(self, model_path: str, model_id: str = "",
                   **kwargs) -> bool:
        """
        Load a model from file.
        
        Args:
            model_path: Path to model file
            model_id: Model identifier
            **kwargs: Additional parameters (gpu_layers, threads, etc.)
            
        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]],
                 config: Optional[GenerationConfig] = None) -> GenerationResult:
        """
        Generate a complete response (non-streaming).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            config: Generation configuration
            
        Returns:
            GenerationResult with the complete text
        """
        pass

    @abstractmethod
    def generate_stream(self, messages: List[Dict[str, str]],
                        config: Optional[GenerationConfig] = None) -> Generator[str, None, None]:
        """
        Generate text with streaming.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            config: Generation configuration
            
        Yields:
            Tokens as they are generated
        """
        pass

    @abstractmethod
    def unload_model(self):
        """Release model resources."""
        pass

    @abstractmethod
    def get_status(self) -> EngineStatus:
        """Get current engine status."""
        pass

    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage in MB. Override for specific implementations."""
        return {"ram_mb": 0.0, "vram_mb": 0.0}

    def _measure_load_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start = time.time()
        result = func(*args, **kwargs)
        self._load_time_ms = (time.time() - start) * 1000
        return result

    def format_messages_for_model(self, messages: List[Dict[str, str]],
                                  system_prompt: str = "",
                                  memory_context: str = "") -> str:
        """
        Format messages into a prompt string for the model.
        Default implementation for chat-format models.
        """
        parts = []

        if system_prompt:
            parts.append(f"System: {system_prompt}")

        if memory_context:
            parts.append(memory_context)

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
            elif role == "system":
                parts.append(f"System: {content}")

        parts.append("Assistant:")
        return "\n".join(parts)


def detect_chat_template(model_id: str = "", model_name: str = "") -> str:
    """
    Detect the chat template family from a model identifier.

    Returns one of: "chatml", "gemma", "phi3".
    """
    text = f"{model_id} {model_name}".lower()
    if "gemma" in text:
        return "gemma"
    if "phi-3" in text or "phi3" in text:
        return "phi3"
    return "chatml"


def build_chat_prompt(messages: List[Dict[str, str]],
                      template: str = "chatml") -> str:
    """Build a model-appropriate chat prompt from messages."""
    system_parts = [m.get("content", "") for m in messages
                    if m.get("role") == "system"]
    system_text = "\n\n".join(p for p in system_parts if p)
    chat = [m for m in messages if m.get("role") in ("user", "assistant")]

    if template == "gemma":
        # Gemma has no system role; fold it into the first user turn.
        parts = []
        for i, msg in enumerate(chat):
            content = msg.get("content", "")
            if msg["role"] == "user":
                if i == 0 and system_text:
                    content = f"{system_text}\n\n{content}"
                parts.append(f"<start_of_turn>user\n{content}<end_of_turn>")
            else:
                parts.append(f"<start_of_turn>model\n{content}<end_of_turn>")
        parts.append("<start_of_turn>model\n")
        return "\n".join(parts)

    if template == "phi3":
        parts = []
        if system_text:
            parts.append(f"<|system|>\n{system_text}<|end|>")
        for msg in chat:
            if msg["role"] == "user":
                parts.append(f"<|user|>\n{msg.get('content', '')}<|end|>")
            else:
                parts.append(f"<|assistant|>\n{msg.get('content', '')}<|end|>")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    # Default: ChatML (Qwen and most instruct models)
    parts = []
    if system_text:
        parts.append(f"<|im_start|>system\n{system_text}<|im_end|>")
    for msg in chat:
        parts.append(
            f"<|im_start|>{msg['role']}\n{msg.get('content', '')}<|im_end|>"
        )
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


def stop_sequences_for(template: str) -> List[str]:
    """Get stop sequences matching the given chat template."""
    stops = ["</s>", "User:", "\nUser:"]
    if template == "gemma":
        stops.insert(0, "<end_of_turn>")
    elif template == "phi3":
        stops.insert(0, "<|end|>")
        stops.insert(1, "<|endoftext|>")
    else:
        stops.insert(0, "<|im_end|>")
        stops.insert(1, "<|end|>")
    return stops
