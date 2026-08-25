"""Metadata capsule with an explicit native-restore capability flag."""
from __future__ import annotations
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

class StateCapsule:
    def __init__(self, path: Path, manifest: dict):
        self.path, self.manifest = path, manifest

    @classmethod
    def create_ollama_metadata(cls, path: Path, model: str) -> "StateCapsule":
        path.mkdir(parents=True, exist_ok=True)
        manifest = {"format": "decastate", "format_version": "0.1",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "model": {"id": model}, "runtime": {"name": "ollama", "host": platform.node()},
                    "restore": {"supported": False,
                                "reason": "Ollama API context is not native persisted inference state"}}
        (path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return cls(path, manifest)

    @classmethod
    def load(cls, path: Path) -> "StateCapsule":
        return cls(path, json.loads((path / "manifest.json").read_text()))
