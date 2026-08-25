"""Environment diagnostics for Phase 0."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def _mlx_device() -> str:
    try:
        import mlx.core as mx  # type: ignore
        return str(mx.default_device())
    except Exception:
        return "unknown"


def _apple_chip() -> str:
    """Real chip name (e.g. 'Apple M4 Max') on macOS; falls back to the CPU arch."""
    if platform.system() == "Darwin":
        try:
            brand = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=5
            ).strip()
            if brand:
                return brand
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.machine() or "unknown"


def _memory_gb() -> str:
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        return f"{round(total / 1024**3)} GB"
    except (ValueError, OSError, AttributeError):
        return "unknown"


def doctor_report() -> dict[str, str]:
    home = Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate"))
    free = shutil.disk_usage(home if home.exists() else Path.home()).free
    ollama = shutil.which("ollama")
    report = {
        "macOS": platform.mac_ver()[0] or "unknown",
        "chip": _apple_chip(),
        "memory": _memory_gb(),
        "python": platform.python_version(),
        "mlx": _version("mlx"),
        "mlx-lm": _version("mlx-lm"),
        "safetensors": _version("safetensors"),
        "device": _mlx_device(),
        "disk_free_bytes": str(free),
        "decastate_home": str(home),
        "model_cache": "present" if (home / "models").exists() else "unknown",
        "ollama": "installed" if ollama else "not installed",
    }
    if ollama:
        try:
            report["ollama_version"] = subprocess.check_output([ollama, "--version"], text=True).strip()
            models = subprocess.check_output([ollama, "list"], text=True, timeout=10)
            report["ollama_models"] = str(max(0, len(models.strip().splitlines()) - 1))
        except (OSError, subprocess.SubprocessError):
            report["ollama_version"] = "unknown"
            report["ollama_models"] = "unknown"
    for key, value in report.items():
        print(f"{key}: {value}")
    return report
