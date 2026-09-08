"""Durable local storage helpers."""
from __future__ import annotations
import fcntl
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from decastate.utils.hashing import sha256_file

# save_prompt_cache is imported lazily inside atomic_save_prompt_cache so that
# importing this module (used by fork/manager) stays stdlib-only — the gateway,
# guard, hub, and fork paths don't need MLX just to import.

@contextmanager
def state_lock(home: Path, state_id: str):
    lock_dir = home / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{state_id}.lock"
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

def atomic_save_prompt_cache(path: Path, cache: list, metadata: dict) -> dict:
    from mlx_lm.models.cache import save_prompt_cache  # lazy: only when actually saving MLX state
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.stem}.{uuid.uuid4().hex}.safetensors"
    try:
        save_prompt_cache(str(temp_path), cache, metadata)
        with temp_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    finally:
        temp_path.unlink(missing_ok=True)

def atomic_copy(source: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, target)
        return {"bytes": target.stat().st_size, "sha256": sha256_file(target)}
    finally:
        temp_path.unlink(missing_ok=True)
