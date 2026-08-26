"""
EdgeMind NPU - Resource Monitor Widget
Displays real-time system resource usage.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel,
)
from PySide6.QtCore import QTimer

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceMonitor(QWidget):
    """Bottom bar showing system resource usage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resourceMonitor")
        self._setup_ui()

        # Prime the CPU counter so subsequent non-blocking calls return
        # a meaningful delta instead of 0.
        if PSUTIL_AVAILABLE:
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass

        # Timer for periodic updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(3000)  # Update every 3 seconds

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(24)

        # RAM
        self.ram_label = QLabel("💾 RAM: --")
        self.ram_label.setObjectName("resourceText")
        self.ram_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        layout.addWidget(self.ram_label)

        # CPU
        self.cpu_label = QLabel("🖥️ CPU: --")
        self.cpu_label.setObjectName("resourceText")
        self.cpu_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        layout.addWidget(self.cpu_label)

        # GPU/VRAM
        self.gpu_label = QLabel("🎮 GPU: --")
        self.gpu_label.setObjectName("resourceText")
        self.gpu_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        layout.addWidget(self.gpu_label)

        # NPU
        self.npu_label = QLabel("🧠 NPU: --")
        self.npu_label.setObjectName("resourceText")
        self.npu_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        layout.addWidget(self.npu_label)

        layout.addStretch()

        # Backend info
        self.backend_label = QLabel("Backend: --")
        self.backend_label.setObjectName("resourceText")
        self.backend_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        layout.addWidget(self.backend_label)

    def _update_stats(self):
        """Update resource usage statistics."""
        if not PSUTIL_AVAILABLE:
            return

        try:
            # RAM
            mem = psutil.virtual_memory()
            ram_used = mem.used / (1024 ** 3)
            ram_total = mem.total / (1024 ** 3)
            ram_percent = mem.percent
            self.ram_label.setText(
                f"💾 RAM: {ram_used:.1f}/{ram_total:.1f} GB ({ram_percent:.0f}%)"
            )

            # CPU (non-blocking; uses the interval since the last call)
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count(logical=True)
            self.cpu_label.setText(
                f"🖥️ CPU: {cpu_percent:.0f}% ({cpu_count} threads)"
            )

        except Exception:
            pass

    def set_gpu_info(self, text: str):
        """Update GPU info text."""
        self.gpu_label.setText(f"🎮 GPU: {text}")

    def set_npu_info(self, text: str):
        """Update NPU info text."""
        self.npu_label.setText(f"🧠 NPU: {text}")

    def set_backend(self, name: str, device: str = ""):
        """Update backend display."""
        text = f"Backend: {name}"
        if device:
            text += f" ({device})"
        self.backend_label.setText(text)
