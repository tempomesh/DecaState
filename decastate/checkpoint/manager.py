"""Immutable native-MLX checkpoint storage and rollback."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mlx_lm.models.cache import load_prompt_cache
import mlx.core as mx
from decastate.storage.local import atomic_save_prompt_cache, state_lock
from decastate.utils.hashing import sha256_file


class CheckpointError(RuntimeError):
    pass


class CheckpointManager:
    def __init__(self, state_root: Path, state_id: str, model_id: str, runtime_version: str = "mlx-lm-0.31.3"):
        self.state_root = state_root
        self.state_id = state_id
        self.model_id = model_id
        self.runtime_version = runtime_version
        self.root = state_root / "checkpoints" / state_id
        self.root.mkdir(parents=True, exist_ok=True)

    def _manifests(self) -> list[Path]:
        return sorted(self.root.glob("*/manifest.json"))

    def _read(self, checkpoint_name: str) -> dict:
        path = self.root / checkpoint_name / "manifest.json"
        if not path.exists():
            raise CheckpointError(f"checkpoint not found: {checkpoint_name}")
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckpointError(f"checkpoint manifest is corrupt: {checkpoint_name}") from exc

    def create(self, checkpoint_name: str, cache: list, context_tokens: int,
               parent_checkpoint_id: str | None = None, provenance: dict | None = None) -> dict:
        if not checkpoint_name or "/" in checkpoint_name or checkpoint_name in {".", ".."}:
            raise CheckpointError("invalid checkpoint name")
        if (self.root / checkpoint_name).exists():
            raise CheckpointError(f"checkpoint already exists: {checkpoint_name}")
        with state_lock(self.state_root, self.state_id):
            if (self.root / checkpoint_name).exists():
                raise CheckpointError(f"checkpoint already exists: {checkpoint_name}")
            checkpoint_id = uuid.uuid4().hex
            directory = self.root / checkpoint_name
            directory.mkdir()
            state_path = directory / "native-cache.safetensors"
            started = time.perf_counter()
            metadata = {"model_id": self.model_id, "runtime_version": self.runtime_version,
                        "state_id": self.state_id, "checkpoint_id": checkpoint_id}
            mx.eval([c.state for c in cache])
            file_info = atomic_save_prompt_cache(state_path, cache, metadata)
            manifest = {
            "checkpoint_id": checkpoint_id,
            "state_id": self.state_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "checkpoint_name": checkpoint_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_fingerprint": {"model_id": self.model_id},
            "runtime_fingerprint": {"name": "mlx", "version": self.runtime_version},
            "context": {"token_count": context_tokens, "cache_position": int(cache[0].offset)},
            "native_state": {"object": "mlx_lm_prompt_cache", "file": "native-cache.safetensors"},
            "state_size_bytes": file_info["bytes"],
            "integrity": {"sha256": file_info["sha256"]},
            "provenance": provenance or {},
            "creation_seconds": time.perf_counter() - started,
        }
            (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            return manifest

    def list(self) -> list[dict]:
        result = []
        for path in self._manifests():
            try:
                result.append(json.loads(path.read_text()))
            except (OSError, json.JSONDecodeError) as exc:
                raise CheckpointError(f"corrupt checkpoint manifest: {path}") from exc
        return result

    def load(self, checkpoint_name: str, expected_model_id: str | None = None) -> tuple[list, dict]:
        manifest = self._read(checkpoint_name)
        expected = expected_model_id or self.model_id
        if manifest.get("model_fingerprint", {}).get("model_id") != expected:
            raise CheckpointError("FINGERPRINT_MISMATCH: checkpoint model does not match runtime model")
        state_path = self.root / checkpoint_name / manifest["native_state"]["file"]
        if not state_path.exists():
            raise CheckpointError(f"native checkpoint state missing: {checkpoint_name}")
        expected_sha = manifest.get("integrity", {}).get("sha256")
        if expected_sha and sha256_file(state_path) != expected_sha:
            raise CheckpointError(f"native checkpoint integrity failure: {checkpoint_name}")
        try:
            cache, metadata = load_prompt_cache(str(state_path), return_metadata=True)
        except Exception as exc:
            raise CheckpointError(f"native checkpoint state is corrupt: {checkpoint_name}") from exc
        if metadata.get("model_id") != expected:
            raise CheckpointError("FINGERPRINT_MISMATCH: serialized state metadata does not match")
        return cache, manifest
