"""End-user native MLX state workspace lifecycle."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache, save_prompt_cache
from decastate.storage.local import atomic_save_prompt_cache, state_lock
from decastate.utils.hashing import sha256_file


class NativeWorkspaceError(RuntimeError):
    pass


class NativeWorkspace:
    def __init__(self, home: Path, state_id: str):
        self.home, self.state_id = home, state_id
        self.path = home / "states" / state_id
        self.live_path = self.path / "live-cache.safetensors"
        self.manifest_path = self.path / "manifest.json"

    @classmethod
    def from_env(cls, state_id: str) -> "NativeWorkspace":
        return cls(Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate")), state_id)

    def exists(self) -> bool:
        return self.live_path.exists() and self.manifest_path.exists()

    def manifest(self) -> dict:
        if not self.manifest_path.exists():
            raise NativeWorkspaceError(f"native state does not exist: {self.state_id}")
        try:
            return json.loads(self.manifest_path.read_text())
        except json.JSONDecodeError as exc:
            raise NativeWorkspaceError("native state manifest is corrupt") from exc

    def _save(self, cache: list, metadata: dict) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        mx.eval([c.state for c in cache])
        atomic_save_prompt_cache(self.live_path, cache, metadata)

    @classmethod
    def create(cls, state_id: str, model_id: str, context_file: Path) -> "NativeWorkspace":
        workspace = cls.from_env(state_id)
        with state_lock(workspace.home, state_id):
            if workspace.exists():
                raise NativeWorkspaceError(f"native state already exists: {state_id}")
            model, tokenizer = load(model_id)
            text = context_file.read_text(errors="replace")
            tokens = tokenizer.encode(text, add_special_tokens=True)
            cache = make_prompt_cache(model)
            started = time.perf_counter()
            list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
            mx.eval([c.state for c in cache])
            workspace._save(cache, {"model_id": model_id, "state_id": state_id, "token_count": str(len(tokens))})
            manifest = {"format": "decastate", "format_version": "0.1", "state_id": state_id,
                    "model": {"id": model_id}, "runtime": {"name": "mlx", "version": "mlx-lm-0.31.3"},
                    "context": {"token_count": len(tokens), "cache_position": int(cache[0].offset)},
                    "source": {"context_file": str(context_file)},
                    "restore": {"supported": True, "mode": "native-mlx"},
                        "last_operation": {"name": "create", "seconds": time.perf_counter() - started},
                        "integrity": {"live_state_sha256": sha256_file(workspace.live_path)}}
            workspace.path.mkdir(parents=True, exist_ok=True)
            workspace.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        return workspace

    def continue_generation(self, prompt: str, max_tokens: int = 32) -> str:
        with state_lock(self.home, self.state_id):
            manifest = self.manifest()
            if manifest.get("integrity", {}).get("live_state_sha256") and sha256_file(self.live_path) != manifest["integrity"]["live_state_sha256"]:
                raise NativeWorkspaceError("live native state integrity check failed")
            model_id = manifest["model"]["id"]
            model, tokenizer = load(model_id)
            cache, metadata = load_prompt_cache(str(self.live_path), return_metadata=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False)
            started = time.perf_counter()
            generated = []
            for token, _ in generate_step(mx.array(inputs, dtype=mx.uint32), model, max_tokens=max_tokens,
                                          prompt_cache=cache):
                generated.append(int(token))
            self._save(cache, {"model_id": model_id, "state_id": self.state_id,
                               "token_count": str(int(manifest["context"]["token_count"]) + len(inputs) + len(generated))})
            manifest["context"]["token_count"] += len(inputs) + len(generated)
            manifest["context"]["cache_position"] = int(cache[0].offset)
            manifest["last_operation"] = {"name": "continue", "prompt_tokens": len(inputs),
                                           "generated_tokens": len(generated), "seconds": time.perf_counter() - started}
            manifest["integrity"] = {"live_state_sha256": sha256_file(self.live_path)}
            self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            return tokenizer.decode(generated)

    def status(self) -> dict:
        manifest = self.manifest()
        manifest["state_size_bytes"] = self.live_path.stat().st_size
        return manifest
