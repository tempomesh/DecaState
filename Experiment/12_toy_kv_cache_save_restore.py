"""STEP 12 LESSON — save and restore a toy K/V cache.

This is the bridge to DecaState. For each processed token, we create a small
K and V number, keep them in a cache, save the cache as JSON, and restore it in
a child process. The child receives only the new token after restoration.

The values are educational scalars, not MLX tensors. The real DecaState proof
uses MLX-LM's native prompt-cache serialization and real Qwen K/V tensors.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def make_kv(token: str, position: int) -> dict[str, float | int | str]:
    """Create deterministic toy K/V values for one token."""
    number = sum(ord(character) for character in token)
    return {"token": token, "position": position, "K": number / 100.0, "V": number / 50.0}


def prefill(tokens: list[str]) -> list[dict[str, float | int | str]]:
    """Process the old prompt and create one K/V record per token."""
    return [make_kv(token, position) for position, token in enumerate(tokens)]


def restore_process(path: str) -> None:
    """Process B: load old K/V and process only a new continuation token."""
    payload = json.loads(Path(path).read_text())
    cache = payload["cache"]
    new_token = payload["new_token"]
    next_position = len(cache)
    cache.append(make_kv(new_token, next_position))
    print("PROCESS B · RESTORE")
    print("  loaded old cache tokens:", [item["token"] for item in cache[:-1]])
    print("  old prompt recomputed: 0 tokens")
    print("  new token processed:", new_token)
    print("  cache after continuation:", [item["token"] for item in cache])
    assert [item["token"] for item in cache] == ["I", "like", "tea"]


def main() -> None:
    print("STEP 12 · TOY K/V CACHE SAVE AND RESTORE")
    print("=" * 58)
    prompt = ["I", "like"]
    cache = prefill(prompt)
    print("PROCESS A · PREFILL")
    print("  prompt:", prompt)
    print("  created K/V:", cache)
    print()
    print("ASCII FLOW")
    print("  'I like' → prefill → K/V cache")
    print("                    │")
    print("                    ▼ save to disk")
    print("                 process dies")
    print("                    │")
    print("                    ▼")
    print("  Process B → load cache → process only 'tea'")
    print()
    with tempfile.TemporaryDirectory(prefix="decastate-toy-") as directory:
        path = Path(directory) / "toy-cache.json"
        path.write_text(json.dumps({"cache": cache, "new_token": "tea"}, indent=2))
        print("saved file:", path)
        child = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--restore", str(path)],
            check=True,
            text=True,
            capture_output=True,
        )
        print(child.stdout, end="")
    print("NOT YET")
    print("  This uses JSON scalars, not native MLX tensors.")
    print("  The production DecaState experiment uses native-cache.safetensors.")
    print("\nTEST PASS: Process B restored old K/V and appended only the new token.")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--restore":
        restore_process(sys.argv[2])
    else:
        main()
