"""Measured long-context cold-vs-native-wake benchmark."""
from __future__ import annotations

import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache, save_prompt_cache

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
SEED_TEXT = "DecaState preserves real native inference state across process boundaries. "


def prefill(model, tokens):
    cache = make_prompt_cache(model)
    start = time.perf_counter()
    list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    return cache, time.perf_counter() - start


def continue_once(model, cache, probe):
    start = time.perf_counter()
    items = list(generate_step(mx.array([probe], dtype=mx.uint32), model, max_tokens=4, prompt_cache=cache))
    return [int(token) for token, _ in items], time.perf_counter() - start


def main():
    model, tokenizer = load(MODEL_ID)
    seed = tokenizer.encode(SEED_TEXT, add_special_tokens=True)
    targets = [128, 512, 1024, 2048]
    rows = []
    state_dir = Path(".decastate/long-context")
    state_dir.mkdir(parents=True, exist_ok=True)
    for target in targets:
        tokens = (seed * ((target // len(seed)) + 1))[:target]
        prefix, probe = tokens[:-1], tokens[-1]
        cold_cache, cold_prefill = prefill(model, prefix)
        state_path = state_dir / f"prompt-cache-{target}.safetensors"
        save_start = time.perf_counter()
        save_prompt_cache(str(state_path), cold_cache, {"model_id": MODEL_ID, "token_count": str(len(prefix))})
        mx.eval([c.state for c in cold_cache])
        save_seconds = time.perf_counter() - save_start
        native_tokens, cold_continue = continue_once(model, cold_cache, probe)
        load_start = time.perf_counter()
        restored_cache, metadata = load_prompt_cache(str(state_path), return_metadata=True)
        load_seconds = time.perf_counter() - load_start
        wake_tokens, wake_seconds = continue_once(model, restored_cache, probe)
        rows.append({
            "model_id": MODEL_ID,
            "context_tokens": target,
            "prefill_tokens": len(prefix),
            "cold_prefill_seconds": cold_prefill,
            "cold_continuation_seconds": cold_continue,
            "save_seconds": save_seconds,
            "load_seconds": load_seconds,
            "wake_continuation_seconds": wake_seconds,
            "cold_total_seconds": cold_prefill + cold_continue,
            "wake_total_seconds": load_seconds + wake_seconds,
            "resume_speedup": (cold_prefill + cold_continue) / (load_seconds + wake_seconds),
            "state_size_bytes": state_path.stat().st_size,
            "fidelity_exact_tokens": native_tokens == wake_tokens,
            "avoided_prefill_tokens": len(prefix),
            "avoided_prefill_ratio": 1.0,
            "metadata_model_id": metadata.get("model_id"),
        })
    output = Path("benchmarks/results/long_context_resume.json")
    output.write_text(json.dumps({"model_id": MODEL_ID, "rows": rows}, indent=2) + "\n")
    print(output.read_text())


if __name__ == "__main__":
    main()
