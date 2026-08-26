"""
EdgeMind NPU - Hardware Detection
Detects available hardware accelerators and selects the best backend.
"""

import os
import csv
import io
import platform
import subprocess
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)

# Prevent a console window from flashing when spawning helpers on Windows
_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class BackendType(Enum):
    """Supported inference backends."""
    OPENVINO_NPU = "openvino_npu"
    OPENVINO_GPU = "openvino_gpu"
    OPENVINO_CPU = "openvino_cpu"
    LLAMACPP_GPU = "llamacpp_gpu"
    LLAMACPP_CPU = "llamacpp_cpu"
    ONNX_DIRECTML = "onnx_directml"


class HardwareTier(Enum):
    """Hardware capability tiers."""
    HIGH = "high"       # NPU + Discrete GPU + 16GB+ RAM
    MEDIUM = "medium"   # iGPU + 8GB+ RAM
    LOW = "low"         # CPU only + 4GB+ RAM
    INSUFFICIENT = "insufficient"  # Below minimum requirements


@dataclass
class CPUInfo:
    """CPU information."""
    name: str = "Unknown"
    manufacturer: str = "Unknown"
    cores_physical: int = 0
    cores_logical: int = 0
    frequency_mhz: float = 0.0
    is_intel_core_ultra: bool = False
    has_npu: bool = False
    npu_name: str = ""


@dataclass
class GPUInfo:
    """GPU information."""
    name: str = "Unknown"
    manufacturer: str = "Unknown"
    vram_mb: int = 0
    driver_version: str = ""
    is_intel_arc: bool = False
    is_intel_uhd: bool = False
    is_nvidia: bool = False
    is_amd: bool = False
    supports_directml: bool = False
    supports_opencl: bool = False


@dataclass
class NPUInfo:
    """NPU information."""
    available: bool = False
    name: str = "Not detected"
    driver_version: str = ""
    vendor: str = ""


@dataclass
class SystemInfo:
    """Complete system hardware information."""
    os_name: str = ""
    os_version: str = ""
    cpu: CPUInfo = field(default_factory=CPUInfo)
    gpus: List[GPUInfo] = field(default_factory=list)
    npu: NPUInfo = field(default_factory=NPUInfo)
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    tier: HardwareTier = HardwareTier.INSUFFICIENT


class HardwareDetector:
    """Detects system hardware and determines available backends."""

    def __init__(self):
        self._system_info: Optional[SystemInfo] = None

    def detect(self) -> SystemInfo:
        """Run full hardware detection."""
        info = SystemInfo()

        # OS
        info.os_name = platform.system()
        info.os_version = platform.version()

        # RAM
        info.ram_total_gb, info.ram_available_gb = self._get_ram_info()

        # CPU
        info.cpu = self._detect_cpu()

        # GPU
        info.gpus = self._detect_gpus()

        # NPU (Intel Core Ultra specific)
        info.npu = self._detect_npu()

        # Determine tier
        info.tier = self._determine_tier(info)

        self._system_info = info
        logger.info(f"Hardware detected: Tier={info.tier.value}, "
                     f"CPU={info.cpu.name}, GPUs={len(info.gpus)}, "
                     f"NPU={'Yes' if info.npu.available else 'No'}")

        return info

    @property
    def system_info(self) -> SystemInfo:
        if self._system_info is None:
            return self.detect()
        return self._system_info

    @staticmethod
    def _run_command(cmd: List[str], timeout: int = 5) -> Optional[str]:
        """Run a helper command and return stdout, or None on failure."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.debug(f"Command failed ({cmd[0]}): {e}")
        return None

    def _query_video_controllers(self) -> List[Dict[str, str]]:
        """Query Win32_VideoController via PowerShell CIM (wmic fallback).

        Returns a list of dicts with keys: name, adapterram, driverversion.
        """
        ps_cmd = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, AdapterRAM, DriverVersion | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        output = self._run_command(
            ["powershell", "-NoProfile", "-Command", ps_cmd]
        )

        rows: List[Dict[str, str]] = []
        if output and "Name" in output:
            try:
                reader = csv.DictReader(io.StringIO(output))
                for row in reader:
                    name = (row.get("Name") or "").strip()
                    if not name:
                        continue
                    rows.append({
                        "name": name,
                        "adapterram": (row.get("AdapterRAM") or "0").strip(),
                        "driverversion": (row.get("DriverVersion") or "").strip(),
                    })
                if rows:
                    return rows
            except Exception as e:
                logger.debug(f"CIM CSV parse error: {e}")

        # Fallback for systems where PowerShell is unavailable/blocked
        output = self._run_command(
            ["wmic", "path", "win32_videocontroller", "get",
             "name,adapterram,driverversion", "/format:csv"]
        )
        if output:
            try:
                reader = csv.DictReader(io.StringIO(output))
                for row in reader:
                    name = (row.get("Name") or "").strip()
                    if not name or name.upper() == "NAME":
                        continue
                    rows.append({
                        "name": name,
                        "adapterram": (row.get("AdapterRAM") or "0").strip(),
                        "driverversion": (row.get("DriverVersion") or "").strip(),
                    })
            except Exception as e:
                logger.debug(f"wmic CSV parse error: {e}")

        return rows

    def _get_ram_info(self) -> tuple:
        """Get total and available RAM in GB."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.total / (1024**3), mem.available / (1024**3)
        except ImportError:
            return 0.0, 0.0

    def _detect_cpu(self) -> CPUInfo:
        """Detect CPU information."""
        info = CPUInfo()

        try:
            info.name = platform.processor() or "Unknown"
            try:
                import psutil
                info.cores_physical = psutil.cpu_count(logical=False) or 0
                info.cores_logical = psutil.cpu_count(logical=True) or 0
            except Exception:
                info.cores_physical = os.cpu_count() or 0
                info.cores_logical = os.cpu_count() or 0

            # Check for Intel Core Ultra
            cpu_name_lower = info.name.lower()
            if "intel" in cpu_name_lower:
                info.manufacturer = "Intel"
                if "ultra" in cpu_name_lower:
                    info.is_intel_core_ultra = True
                    info.has_npu = True
                    info.npu_name = "Intel AI Boost (NPU)"
            elif "amd" in cpu_name_lower:
                info.manufacturer = "AMD"

        except Exception as e:
            logger.error(f"CPU detection error: {e}")

        return info

    def _detect_gpus(self) -> List[GPUInfo]:
        """Detect available GPUs."""
        gpus = []

        # Try to detect NVIDIA GPUs
        nvidia_gpus = self._detect_nvidia_gpu()
        if nvidia_gpus:
            gpus.extend(nvidia_gpus)

        # Try to detect AMD GPUs
        amd_gpus = self._detect_amd_gpu()
        if amd_gpus:
            gpus.extend(amd_gpus)

        # Try to detect Intel integrated/Arc GPUs
        intel_gpus = self._detect_intel_gpu()
        if intel_gpus:
            gpus.extend(intel_gpus)

        # If no specific detection worked, create a generic entry
        if not gpus:
            gpu = GPUInfo(name="Generic GPU", manufacturer="Unknown")
            gpus.append(gpu)

        return gpus

    def _detect_nvidia_gpu(self) -> List[GPUInfo]:
        """Detect NVIDIA GPUs via nvidia-smi."""
        gpus = []
        output = self._run_command(
            ["nvidia-smi",
             "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader,nounits"]
        )
        if output:
            for line in output.strip().split("\n"):
                if line.strip():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        try:
                            vram_mb = int(float(parts[1]))
                        except ValueError:
                            vram_mb = 0
                        gpus.append(GPUInfo(
                            name=parts[0],
                            manufacturer="NVIDIA",
                            vram_mb=vram_mb,
                            driver_version=parts[2],
                            is_nvidia=True,
                            supports_directml=False,
                        ))
        return gpus

    def _detect_amd_gpu(self) -> List[GPUInfo]:
        """Detect AMD GPUs."""
        gpus = []
        try:
            if platform.system() == "Windows":
                for row in self._query_video_controllers():
                    name_lower = row["name"].lower()
                    if "amd" in name_lower or "radeon" in name_lower:
                        gpu = GPUInfo(
                            name=row["name"],
                            manufacturer="AMD",
                            driver_version=row.get("driverversion", ""),
                            is_amd=True,
                            supports_directml=True,
                        )
                        try:
                            gpu.vram_mb = int(float(row.get("adapterram", 0) or 0)) // (1024 * 1024)
                        except (ValueError, TypeError):
                            pass
                        gpus.append(gpu)
        except Exception as e:
            logger.debug(f"AMD GPU detection: {e}")
        return gpus

    def _detect_intel_gpu(self) -> List[GPUInfo]:
        """Detect Intel GPUs."""
        gpus = []
        try:
            if platform.system() == "Windows":
                for row in self._query_video_controllers():
                    name_lower = row["name"].lower()
                    if "intel" in name_lower:
                        gpu = GPUInfo(
                            name=row["name"],
                            manufacturer="Intel",
                            driver_version=row.get("driverversion", ""),
                            is_intel_uhd=True,
                            supports_directml=True,
                            supports_opencl=True,
                        )
                        try:
                            gpu.vram_mb = int(float(row.get("adapterram", 0) or 0)) // (1024 * 1024)
                        except (ValueError, TypeError):
                            pass
                        if "arc" in name_lower:
                            gpu.is_intel_arc = True
                        gpus.append(gpu)
        except Exception as e:
            logger.debug(f"Intel GPU detection: {e}")
        return gpus

    def _detect_npu(self) -> NPUInfo:
        """Detect NPU availability."""
        info = NPUInfo()

        # Check Intel NPU via OpenVINO
        try:
            import openvino as ov
            core = ov.Core()
            available_devices = core.available_devices

            for device in available_devices:
                if "NPU" in device.upper():
                    info.available = True
                    info.name = "Intel NPU"
                    info.vendor = "Intel"

                    try:
                        device_name = core.get_property(device, "FULL_DEVICE_NAME")
                        info.name = device_name
                    except Exception:
                        pass

                    try:
                        info.driver_version = core.get_property(
                            device, "DRIVER_VERSION"
                        )
                    except Exception:
                        pass

                    break
        except ImportError:
            logger.debug("OpenVINO not available for NPU detection")
        except Exception as e:
            logger.debug(f"NPU detection via OpenVINO: {e}")

        # Fallback: Check for Intel NPU driver on Windows via PowerShell CIM
        if not info.available and platform.system() == "Windows":
            ps_cmd = (
                "Get-CimInstance Win32_PnPEntity | "
                "Where-Object { $_.Name -match 'NPU|Neural|AI Boost' } | "
                "Select-Object -First 1 -ExpandProperty Name"
            )
            output = self._run_command(
                ["powershell", "-NoProfile", "-Command", ps_cmd]
            )
            if output and output.strip():
                info.available = True
                info.name = output.strip()
                info.vendor = "Intel"

        return info

    def _determine_tier(self, info: SystemInfo) -> HardwareTier:
        """Determine hardware capability tier."""
        ram_gb = info.ram_total_gb

        if ram_gb < 4.0:
            return HardwareTier.INSUFFICIENT

        has_npu = info.npu.available
        has_discrete_gpu = any(g.is_nvidia or g.is_intel_arc for g in info.gpus)

        if has_npu and has_discrete_gpu and ram_gb >= 16.0:
            return HardwareTier.HIGH
        elif has_npu or has_discrete_gpu or ram_gb >= 8.0:
            return HardwareTier.MEDIUM
        elif ram_gb >= 4.0:
            return HardwareTier.LOW
        else:
            return HardwareTier.INSUFFICIENT

    def get_available_backends(self) -> List[BackendType]:
        """Get list of available inference backends in priority order."""
        backends = []
        info = self.system_info

        # OpenVINO NPU (highest priority)
        if info.npu.available:
            backends.append(BackendType.OPENVINO_NPU)

        # OpenVINO GPU (Intel iGPU/Arc)
        has_intel_gpu = any(g.manufacturer == "Intel" for g in info.gpus)
        if has_intel_gpu:
            try:
                import openvino as ov
                core = ov.Core()
                if "GPU" in core.available_devices:
                    backends.append(BackendType.OPENVINO_GPU)
            except Exception:
                pass

        # ONNX Runtime DirectML
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if "DmlExecutionProvider" in providers:
                backends.append(BackendType.ONNX_DIRECTML)
        except ImportError:
            pass

        # llama.cpp with GPU
        if info.ram_total_gb >= 4.0:
            has_gpu = any(g.is_nvidia or g.is_intel_arc or g.is_intel_uhd for g in info.gpus)
            if has_gpu:
                backends.append(BackendType.LLAMACPP_GPU)

        # llama.cpp CPU (always available)
        backends.append(BackendType.LLAMACPP_CPU)

        return backends

    def get_best_backend(self) -> BackendType:
        """Get the best available backend."""
        backends = self.get_available_backends()
        return backends[0] if backends else BackendType.LLAMACPP_CPU

    def get_recommended_gpu_layers(self) -> int:
        """Get recommended number of GPU layers based on available VRAM."""
        info = self.system_info

        # Find best GPU VRAM
        max_vram_mb = 0
        for gpu in info.gpus:
            if gpu.vram_mb > max_vram_mb:
                max_vram_mb = gpu.vram_mb

        if max_vram_mb <= 0:
            # Try to estimate from RAM
            if info.ram_total_gb >= 8.0:
                return 20
            return 0

        # Rule of thumb: ~1GB per 12 layers for small models
        if max_vram_mb >= 8000:
            return 99  # Offload all layers
        elif max_vram_mb >= 4000:
            return 20
        elif max_vram_mb >= 2000:
            return 10
        else:
            return 0

    def get_status_text(self) -> str:
        """Get a human-readable hardware status text."""
        info = self.system_info
        lines = []

        lines.append(f"🖥️ CPU: {info.cpu.name}")
        if info.cpu.is_intel_core_ultra:
            lines.append("   ✅ Intel Core Ultra detected (NPU available)")
        lines.append(f"   Cores: {info.cpu.cores_physical} physical, {info.cpu.cores_logical} logical")

        lines.append(f"💾 RAM: {info.ram_total_gb:.1f} GB total, {info.ram_available_gb:.1f} GB available")

        if info.npu.available:
            lines.append(f"🧠 NPU: {info.npu.name}")
            lines.append("   ✅ Ready for AI acceleration")

        for i, gpu in enumerate(info.gpus):
            vram_text = f" ({gpu.vram_mb} MB)" if gpu.vram_mb > 0 else ""
            lines.append(f"🎮 GPU {i+1}: {gpu.name}{vram_text}")

        backends = self.get_available_backends()
        lines.append(f"⚡ Available backends: {', '.join(b.value for b in backends)}")
        lines.append(f"📊 Hardware tier: {info.tier.value.upper()}")

        return "\n".join(lines)
