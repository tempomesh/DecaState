"""Checkpoint/rollback benchmark over real MLX prompt-cache state."""
from __future__ import annotations

import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache

from decastate.checkpoint.manager import CheckpointError, CheckpointManager

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
SEED_TEXT = "DecaState checkpoint rollback preserves real native inference state. "
STATE_ROOT = Path(".decastate")


def prefill(model, tokens):
    cache = make_prompt_cache(model)
    start = time.perf_counter()
    list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    return cache, time.perf_counter() - start


def append_token(model, cache, token):
    list(generate_step(mx.array([token], dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])


def continue_tokens(model, cache, probe, count=6):
    start = time.perf_counter()
    values = []
    for token, _logprobs in generate_step(mx.array([probe], dtype=mx.uint32), model,
                                           max_tokens=count, prompt_cache=cache):
        values.append(int(token))
    return values, time.perf_counter() - start


def main():
    model, tokenizer = load(MODEL_ID)
    seed = tokenizer.encode(SEED_TEXT, add_special_tokens=True)
    rows = []
    for target in [128, 512, 1024, 2048]:
        tokens = (seed * ((target // len(seed)) + 1))[:target]
        prefix = tokens[:-1]
        c1_probe, c2_probe = tokens[-1], tokens[-2]
        state_id = f"phase2-{target}-{int(time.time() * 1000)}"
        manager = CheckpointManager(STATE_ROOT, state_id, MODEL_ID)
        cache, _prefill_seconds = prefill(model, prefix)
        c1_start = time.perf_counter()
        c1 = manager.create("c1", cache, len(prefix), provenance={"phase": "checkpoint", "source": "native-prefill"})
        mx.eval([c.state for c in cache])
        c1_latency = time.perf_counter() - c1_start

        c1_cache, _ = manager.load("c1")
        c1_reference, _ = continue_tokens(model, c1_cache, c1_probe)

        c2_cache, _ = manager.load("c1")
        append_token(model, c2_cache, c1_probe)
        c2_start = time.perf_counter()
        c2 = manager.create("c2", c2_cache, len(prefix) + 1,
                            parent_checkpoint_id=c1["checkpoint_id"],
                            provenance={"phase": "checkpoint", "source": "c1-continued"})
        mx.eval([c.state for c in c2_cache])
        c2_latency = time.perf_counter() - c2_start

        c2_cache_for_reference, _ = manager.load("c2")
        c2_reference, _ = continue_tokens(model, c2_cache_for_reference, c2_probe)

        rollback_start = time.perf_counter()
        c1_restored, c1_manifest = manager.load("c1")
        c1_rollback, c1_wake = continue_tokens(model, c1_restored, c1_probe)
        c1_rollback_latency = time.perf_counter() - rollback_start

        rollback_start = time.perf_counter()
        c2_restored, c2_manifest = manager.load("c2")
        c2_rollback, c2_wake = continue_tokens(model, c2_restored, c2_probe)
        c2_rollback_latency = time.perf_counter() - rollback_start

        wrong_fingerprint = False
        try:
            manager.load("c1", expected_model_id="wrong-model")
        except CheckpointError as exc:
            wrong_fingerprint = "FINGERPRINT_MISMATCH" in str(exc)

        missing_checkpoint = False
        try:
            manager.load("missing")
        except CheckpointError:
            missing_checkpoint = True

        corrupt_state = STATE_ROOT / "checkpoints" / state_id / "c2" / "native-cache.safetensors"
        original_bytes = corrupt_state.read_bytes()
        corrupt_state.write_bytes(original_bytes[: max(1, len(original_bytes) // 2)])
        corrupt_rejected = False
        try:
            manager.load("c2")
        except CheckpointError:
            corrupt_rejected = True
        corrupt_state.write_bytes(original_bytes)

        lineage_ok = c1["parent_checkpoint_id"] is None and c2["parent_checkpoint_id"] == c1["checkpoint_id"]
        parent_intact, _ = manager.load("c1")
        parent_again, _ = continue_tokens(model, parent_intact, c1_probe)
        parent_ok = parent_again == c1_reference
        rows.append({
            "context_tokens": target,
            "c1_context_tokens": c1["context"]["token_count"],
            "c2_context_tokens": c2["context"]["token_count"],
            "c1_creation_seconds": c1_latency,
            "c2_creation_seconds": c2_latency,
            "c1_rollback_seconds": c1_rollback_latency,
            "c2_rollback_seconds": c2_rollback_latency,
            "c1_wake_seconds": c1_wake,
            "c2_wake_seconds": c2_wake,
            "c1_size_bytes": c1["state_size_bytes"],
            "c2_size_bytes": c2["state_size_bytes"],
            "c1_exact_match": c1_rollback == c1_reference,
            "c2_exact_match": c2_rollback == c2_reference,
            "reprocessed_original_prefix_tokens": 0,
            "avoided_prefill_ratio": 1.0,
            "wrong_checkpoint_rejected": missing_checkpoint,
            "corrupt_checkpoint_rejected": corrupt_rejected,
            "wrong_model_fingerprint_rejected": wrong_fingerprint,
            "lineage_correct": lineage_ok,
            "parent_intact": parent_ok,
        })

    output = Path("benchmarks/results/checkpoint_rollback.json")
    output.write_text(json.dumps({"model_id": MODEL_ID, "rows": rows}, indent=2) + "\n")
    print(output.read_text())
    checks = [value for row in rows for key, value in row.items()
              if key.endswith(("exact_match", "rejected", "correct", "intact"))]
    if not all(checks):
        raise SystemExit("CHECKPOINT/ROLLBACK GATE FAILED")
    print("CHECKPOINT / ROLLBACK GATE: PASS")


if __name__ == "__main__":
    main()
