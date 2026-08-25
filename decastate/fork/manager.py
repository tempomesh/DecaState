"""Correctness-first physical-copy fork manager."""
from __future__ import annotations
import json, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from decastate.storage.local import atomic_copy, state_lock

class ForkError(RuntimeError):
    pass

class ForkManager:
    def __init__(self, state_root: Path, state_id: str, model_id: str):
        self.root = state_root / "branches" / state_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_id, self.model_id = state_id, model_id

    def create(self, branch_name: str, source_cache: Path, context_tokens: int) -> dict:
        if not branch_name or "/" in branch_name or (self.root / branch_name).exists():
            raise ForkError(f"invalid or existing branch: {branch_name}")
        with state_lock(self.root.parent.parent, self.state_id):
            if (self.root / branch_name).exists():
                raise ForkError(f"invalid or existing branch: {branch_name}")
            branch = self.root / branch_name
            branch.mkdir()
            started = time.perf_counter()
            target = branch / "native-cache.safetensors"
            file_info = atomic_copy(source_cache, target)
            manifest = {"branch_id": uuid.uuid4().hex, "branch_name": branch_name,
                    "state_id": self.state_id, "parent": "base",
                    "model_fingerprint": {"model_id": self.model_id},
                    "runtime_fingerprint": {"name": "mlx"},
                    "context_token_count": context_tokens,
                    "native_state_file": "native-cache.safetensors",
                    "logical_state_size_bytes": file_info["bytes"],
                    "integrity": {"sha256": file_info["sha256"]},
                    "physical_copy": True, "created_at": datetime.now(timezone.utc).isoformat(),
                    "fork_seconds": time.perf_counter() - started}
            (branch / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            return manifest

    def list(self) -> list[dict]:
        return [json.loads(path.read_text()) for path in sorted(self.root.glob("*/manifest.json"))]
