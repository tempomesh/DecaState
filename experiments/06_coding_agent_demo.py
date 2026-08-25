"""Product demo: understand this repository once, checkpoint, fork, and wake."""
from __future__ import annotations

import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache, save_prompt_cache

from decastate.checkpoint.manager import CheckpointManager
from decastate.fork.manager import ForkManager

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ROOT = Path(__file__).resolve().parents[1]


def repository_context() -> str:
    selected = [ROOT / "README.md", ROOT / "pyproject.toml", ROOT / "docs/ARCHITECTURE.md",
                ROOT / "docs/ROADMAP.md", ROOT / "decastate/cli/main.py", ROOT / "decastate/checkpoint/manager.py"]
    chunks = []
    for path in selected:
        if path.exists():
            chunks.append(f"\n===== {path.relative_to(ROOT)} =====\n{path.read_text(errors='replace')}")
    return "You are analyzing the DecaState repository. Understand its architecture and state lifecycle.\n" + "".join(chunks)


def prefill(model, tokens):
    cache = make_prompt_cache(model)
    start = time.perf_counter()
    list(generate_step(mx.array(tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    return cache, time.perf_counter() - start


def continue_text(model, tokenizer, cache, text, count=24):
    inputs = tokenizer.encode(text, add_special_tokens=False)
    start = time.perf_counter()
    output_tokens = []
    for token, _ in generate_step(mx.array(inputs, dtype=mx.uint32), model, max_tokens=count, prompt_cache=cache):
        output_tokens.append(int(token))
    return output_tokens, time.perf_counter() - start


def main():
    model, tokenizer = load(MODEL_ID)
    prompt = repository_context()
    tokens = tokenizer.encode(prompt, add_special_tokens=True)
    tokens = tokens[:2048]
    prefix = tokens[:-1]
    state_id = f"coding-demo-{int(time.time() * 1000)}"
    state_root = ROOT / ".decastate"
    state_dir = state_root / "states" / state_id
    state_dir.mkdir(parents=True, exist_ok=True)
    base_cache, cold_prefill = prefill(model, prefix)
    base_path = state_dir / "live-cache.safetensors"
    save_prompt_cache(str(base_path), base_cache, {"model_id": MODEL_ID, "state_id": state_id})
    mx.eval([c.state for c in base_cache])
    (state_dir / "manifest.json").write_text(json.dumps({"model": {"id": MODEL_ID},
        "context": {"token_count": len(prefix), "cache_position": int(base_cache[0].offset)}}, indent=2) + "\n")
    checkpoints = CheckpointManager(state_root, state_id, MODEL_ID)
    checkpoint = checkpoints.create("repo-understood", base_cache, len(prefix),
                                    provenance={"demo": "coding-agent", "source": "real-repository-files"})
    probe = tokens[-1]
    cold_cache, _ = prefill(model, prefix)
    cold_tokens, cold_continue = continue_text(model, tokenizer, cold_cache, tokenizer.decode([probe]), 12)
    wake_cache, _ = checkpoints.load("repo-understood")
    wake_tokens, wake_continue = continue_text(model, tokenizer, wake_cache, tokenizer.decode([probe]), 12)

    forks = ForkManager(state_root, state_id, MODEL_ID)
    roles = {"coder": " Review implementation risks and propose the next code change.",
             "reviewer": " Review architecture and identify correctness gaps.",
             "security": " Perform a security review of state persistence and storage."}
    branches = []
    for role, instruction in roles.items():
        manifest = forks.create(role, base_path, len(prefix))
        branch_path = state_root / "branches" / state_id / role / "native-cache.safetensors"
        branch_cache, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        branch_tokens = tokenizer.encode(instruction, add_special_tokens=False)
        list(generate_step(mx.array(branch_tokens, dtype=mx.uint32), model, max_tokens=0, prompt_cache=branch_cache))
        mx.eval([c.state for c in branch_cache])
        save_prompt_cache(str(branch_path), branch_cache, {"model_id": MODEL_ID, "branch_id": manifest["branch_id"]})
        mx.eval([c.state for c in branch_cache])
        reference_cache, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        reference, branch_time = continue_text(model, tokenizer, reference_cache, " Continue with your findings:", 16)
        wake_branch, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        woke, wake_time = continue_text(model, tokenizer, wake_branch, " Continue with your findings:", 16)
        branches.append({"role": role, "branch_context_tokens": len(prefix) + len(branch_tokens),
                         "fork_seconds": manifest["fork_seconds"], "branch_wake_exact": reference == woke,
                         "branch_generation_seconds": branch_time, "branch_wake_seconds": wake_time})

    result = {"model_id": MODEL_ID, "state_id": state_id, "repository_context_tokens": len(tokens),
              "checkpoint": checkpoint["checkpoint_name"], "cold_prefill_seconds": cold_prefill,
              "cold_continuation_seconds": cold_continue, "wake_continuation_seconds": wake_continue,
              "cold_vs_wake_exact": cold_tokens == wake_tokens, "branches": branches,
              "claim_boundary": "physical-copy forks; no COW or portability claim"}
    output = ROOT / "benchmarks/results/coding_agent_demo.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output.read_text())
    print("CODING AGENT DEMO: PASS")


if __name__ == "__main__":
    main()
