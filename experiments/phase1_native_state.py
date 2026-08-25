"""Phase 1 native MLX cache replay and process-death experiment.

This uses the official MLX-LM prompt-cache serialization path. It does not use
Ollama and does not replay the original prompt in the restore process.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import make_prompt_cache, load_prompt_cache, save_prompt_cache

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
PROMPT = (
    "DecaState deterministic state replay test. Remember this exact fact: "
    "the archive marker is BLUE-EMBER-417. Explain why preserving inference "
    "state can reduce repeated prefill work."
)
TOP_K = 10


def tokens_for(tokenizer) -> list[int]:
    return list(tokenizer.encode(PROMPT, add_special_tokens=True))


def top_ids(logprobs) -> list[int]:
    mx.eval(logprobs)
    return [int(x) for x in mx.argsort(logprobs)[-TOP_K:][::-1].tolist()]


def continuation(model, cache, probe: int, count: int = 8) -> dict:
    generated = []
    first_top = []
    started = time.perf_counter()
    stream = generate_step(
        mx.array([probe], dtype=mx.uint32),
        model,
        max_tokens=count,
        prompt_cache=cache,
        sampler=lambda x: mx.argmax(x, axis=-1),
    )
    for token, logprobs in stream:
        generated.append(int(token))
        if not first_top:
            first_top = top_ids(logprobs)
    return {
        "tokens": generated,
        "first_top_k": first_top,
        "elapsed_seconds": time.perf_counter() - started,
    }


def prefill(model, prefix: list[int]) -> tuple[list, float]:
    cache = make_prompt_cache(model)
    started = time.perf_counter()
    list(generate_step(mx.array(prefix, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    return cache, time.perf_counter() - started


def cache_summary(cache: list) -> dict:
    return {
        "classes": [type(c).__name__ for c in cache],
        "layers": len(cache),
        "token_position": int(cache[0].offset),
        "bytes": int(sum(c.nbytes for c in cache)),
        "dtypes": sorted({str(x.dtype) for c in cache for x in c.state if x is not None}),
    }


def process_a(cache_path: Path, result_path: Path) -> None:
    model, tokenizer = load(MODEL_ID)
    tokens = tokens_for(tokenizer)
    prefix, probe = tokens[:-1], tokens[-1]
    cache, prefill_seconds = prefill(model, prefix)
    summary = cache_summary(cache)
    save_prompt_cache(str(cache_path), cache, {"model_id": MODEL_ID, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest()})
    mx.eval([c.state for c in cache])
    reference = continuation(model, cache, probe)
    result = {
        "model_id": MODEL_ID,
        "prompt": PROMPT,
        "prompt_tokens": len(tokens),
        "prefill_tokens": len(prefix),
        "probe_token": probe,
        "prefill_seconds": prefill_seconds,
        "cache": summary,
        "reference": reference,
        "cache_path": str(cache_path),
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n")


def process_b(cache_path: Path, result_path: Path, expected_model: str) -> None:
    model, _tokenizer = load(MODEL_ID)
    result = json.loads(result_path.read_text())
    metadata_cache, metadata = load_prompt_cache(str(cache_path), return_metadata=True)
    if expected_model != MODEL_ID or metadata.get("model_id") != MODEL_ID:
        raise SystemExit("FINGERPRINT_REJECTED: model identity mismatch")
    restored = continuation(model, metadata_cache, int(result["probe_token"]))
    reference = result["reference"]
    agreement = restored["tokens"] == reference["tokens"]
    top1 = bool(restored["first_top_k"] and reference["first_top_k"] and restored["first_top_k"][0] == reference["first_top_k"][0])
    result["restored"] = restored
    result["prefill_avoidance"] = {
        "eligible_prefill_tokens": int(result["prefill_tokens"]),
        "reprocessed_prefill_tokens": 0,
        "avoided_prefill_tokens": int(result["prefill_tokens"]),
        "avoided_prefill_ratio": 1.0,
        "restore_input_tokens": 1,
        "evidence": "Process B loads the serialized KV cache and supplies only the one probe token; original prompt tokens are not passed to the model.",
    }
    result["state_size_bytes"] = cache_path.stat().st_size
    result["process_death_checks"] = {"top1_agreement": top1, "deterministic_continuation_agreement": agreement}
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    if not top1 or not agreement:
        raise SystemExit("FAIL: restored continuation differs from Process A")


def same_process(result_path: Path) -> None:
    model, tokenizer = load(MODEL_ID)
    tokens = tokens_for(tokenizer)
    prefix, probe = tokens[:-1], tokens[-1]
    cache, prefill_seconds = prefill(model, prefix)
    prefill_summary = cache_summary(cache)
    with tempfile.TemporaryDirectory(prefix="decastate-phase1-") as temp:
        cache_path = Path(temp) / "prompt-cache.safetensors"
        save_prompt_cache(str(cache_path), cache, {"model_id": MODEL_ID})
        mx.eval([c.state for c in cache])
        native = continuation(model, cache, probe)
        replay_cache, _metadata = load_prompt_cache(str(cache_path), return_metadata=True)
        replay = continuation(model, replay_cache, probe)
    result = {"model_id": MODEL_ID, "prompt_tokens": len(tokens), "prefill_tokens": len(prefix),
              "prefill_seconds": prefill_seconds, "cache": prefill_summary, "native": native,
              "replay": replay, "top1_agreement": native["first_top_k"][0] == replay["first_top_k"][0],
              "deterministic_continuation_agreement": native["tokens"] == replay["tokens"]}
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    if not result["top1_agreement"] or not result["deterministic_continuation_agreement"]:
        raise SystemExit("FAIL: same-process replay differs")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("same-process", "process-a", "process-b"))
    parser.add_argument("--cache", type=Path, default=Path(".decastate/phase1/prompt-cache.safetensors"))
    parser.add_argument("--result", type=Path, default=Path("benchmarks/results/phase1_native_state.json"))
    parser.add_argument("--expected-model", default=MODEL_ID)
    args = parser.parse_args()
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "same-process":
        same_process(args.result)
    elif args.mode == "process-a":
        process_a(args.cache, args.result)
    else:
        process_b(args.cache, args.result, args.expected_model)


if __name__ == "__main__":
    main()
