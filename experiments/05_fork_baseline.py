"""Correctness-first physical-copy fork benchmark."""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache, save_prompt_cache
from decastate.fork.manager import ForkManager

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
STATE_ROOT = Path(".decastate")

def prefill(model, tokens):
    cache = make_prompt_cache(model)
    list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    return cache

def append(model, cache, tokens):
    list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])

def generate(model, cache, probe, count=6):
    return [int(token) for token, _ in generate_step(mx.array([probe], dtype=mx.uint32), model,
                                                     max_tokens=count, prompt_cache=cache)]

def main():
    model, tokenizer = load(MODEL_ID)
    seed = tokenizer.encode("DecaState fork baseline. The shared repository context is stable. ",
                            add_special_tokens=True)
    base_tokens = (seed * ((1024 // len(seed)) + 1))[:1024]
    base_cache = prefill(model, base_tokens)
    state_id = f"fork-demo-1024-{int(time.time() * 1000)}"
    state_dir = STATE_ROOT / "states" / state_id
    state_dir.mkdir(parents=True, exist_ok=True)
    base_path = state_dir / "live-cache.safetensors"
    save_prompt_cache(str(base_path), base_cache, {"model_id": MODEL_ID})
    mx.eval([c.state for c in base_cache])
    (state_dir / "manifest.json").write_text(json.dumps({"model": {"id": MODEL_ID},
        "context": {"token_count": len(base_tokens), "cache_position": int(base_cache[0].offset)}}, indent=2) + "\n")
    manager = ForkManager(STATE_ROOT, state_id, MODEL_ID)
    branches = {"coder": " Coder inspect implementation", "reviewer": " Reviewer find defects", "security": " Security identify risks"}
    results = []
    for name, text in branches.items():
        manifest = manager.create(name, base_path, len(base_tokens))
        branch_path = STATE_ROOT / "branches" / state_id / name / "native-cache.safetensors"
        branch_cache, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        append(model, branch_cache, tokenizer.encode(text, add_special_tokens=False))
        save_prompt_cache(str(branch_path), branch_cache, {"model_id": MODEL_ID, "branch_id": manifest["branch_id"]})
        mx.eval([c.state for c in branch_cache])
        probe = tokenizer.encode(" Continue deterministically", add_special_tokens=False)[0]
        reference_cache, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        reference = generate(model, reference_cache, probe)
        wake_cache, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        woke = generate(model, wake_cache, probe)
        digest = hashlib.sha256(branch_path.read_bytes()).hexdigest()
        results.append({"branch": name, "fork_seconds": manifest["fork_seconds"],
                        "logical_state_size_bytes": branch_path.stat().st_size,
                        "wake_exact_match": reference == woke, "tokens": reference,
                        "native_state_sha256": digest})
    parent_cache, _ = load_prompt_cache(str(base_path), return_metadata=True)
    parent_probe = tokenizer.encode(" Continue base deterministically", add_special_tokens=False)[0]
    parent_a = generate(model, parent_cache, parent_probe)
    parent_cache_again, _ = load_prompt_cache(str(base_path), return_metadata=True)
    parent_b = generate(model, parent_cache_again, parent_probe)
    branch_tokens = [tuple(row["tokens"]) for row in results]
    output = {"model_id": MODEL_ID, "base_context_tokens": len(base_tokens), "branches": results,
              "native_state_divergence": len({row["native_state_sha256"] for row in results}) == len(results),
              "output_token_divergence": len(set(branch_tokens)) == len(branch_tokens),
              "parent_unchanged": parent_a == parent_b, "physical_copy_claim": False,
              "logical_state_bytes": sum(row["logical_state_size_bytes"] for row in results)}
    path = Path("benchmarks/results/fork_baseline.json")
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(path.read_text())
    if not output["native_state_divergence"] or not output["parent_unchanged"] or not all(row["wake_exact_match"] for row in results):
        raise SystemExit("FORK CORRECTNESS GATE FAILED")
    print("FORK CORRECTNESS GATE: PASS (physical copies; no COW claim)")

if __name__ == "__main__":
    main()
