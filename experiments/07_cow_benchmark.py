"""Measure APFS clonefile sharing over a real native MLX cache artifact."""
from __future__ import annotations
import json, time
from pathlib import Path
import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import make_prompt_cache, save_prompt_cache
from decastate.fork.copy_on_write import allocated_bytes, clone_file, logical_bytes

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ROOT = Path(".decastate/cow-research")

def main():
    model, tokenizer = load(MODEL_ID)
    seed = tokenizer.encode("DecaState COW research uses a real native MLX cache. ", add_special_tokens=True)
    tokens = (seed * ((2048 // len(seed)) + 1))[:2048]
    cache = make_prompt_cache(model)
    list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    run_root = ROOT / str(int(time.time() * 1000))
    run_root.mkdir(parents=True)
    base = run_root / "base-native-cache.safetensors"
    save_prompt_cache(str(base), cache, {"model_id": MODEL_ID})
    mx.eval([c.state for c in cache])
    branches = []
    for name in ("coder", "reviewer", "security"):
        target = run_root / f"{name}-clone.safetensors"
        started = time.perf_counter()
        clone_supported = clone_file(base, target)
        fork_seconds = time.perf_counter() - started
        before = allocated_bytes(target)
        with target.open("r+b") as handle:
            handle.seek(0)
            first = handle.read(1)
            handle.seek(0)
            handle.write(bytes([(first[0] ^ 1) if first else 1]))
            handle.flush()
        after = allocated_bytes(target)
        branches.append({"branch": name, "clone_supported": clone_supported,
                         "fork_seconds": fork_seconds, "logical_bytes": logical_bytes(target),
                         "physical_bytes_before_mutation": before,
                         "physical_bytes_after_one_byte_mutation": after,
                         "native_kv_cow_proven": False})
    base_physical = allocated_bytes(base)
    logical_total = logical_bytes(base) + sum(row["logical_bytes"] for row in branches)
    physical_initial = base_physical + sum(row["physical_bytes_before_mutation"] for row in branches)
    physical_after = base_physical + sum(row["physical_bytes_after_one_byte_mutation"] for row in branches)
    result = {"model_id": MODEL_ID, "context_tokens": len(tokens),
              "base_logical_bytes": logical_bytes(base), "base_physical_bytes": base_physical,
              "logical_total_bytes": logical_total, "physical_total_before_mutation": physical_initial,
              "physical_total_after_one_byte_mutation": physical_after,
              "initial_logical_to_physical_ratio": logical_total / physical_initial if physical_initial else None,
              "branches": branches,
              "claim_boundary": "APFS/file clone primitive measured; native KV copy-on-write not integrated or claimed"}
    output = Path("benchmarks/results/cow_research.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output.read_text())
    print("COW STORAGE RESEARCH: COMPLETE; NATIVE KV COW CLAIM: NOT MADE")

if __name__ == "__main__":
    main()
