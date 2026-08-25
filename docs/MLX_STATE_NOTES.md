# MLX State Notes

Phase 0 placeholder. This document will contain exact installed MLX/MLX-LM versions, Qwen implementation paths, cache classes, tensor layout, position handling, and serialization findings after local inspection.

## Existing local model inventory

Ollama is installed (`0.32.15`) and currently contains `qwen2.5:14b` (9.0 GB). No additional model download is authorized or required at this stage.

## Execution boundary

Ollama model listing and metadata inspection are non-inference checks. GPU/model execution requires explicit user permission before it is run.

## Installed MLX-LM inspection — 2026-08-23

Environment:

```text
mlx 0.32.1
mlx-lm 0.31.3
```

Relevant installed source:

```text
mlx_lm/models/qwen2.py
mlx_lm/models/cache.py
mlx_lm/cache_prompt.py
mlx_lm/generate.py
```

For the installed Qwen2 implementation, `Qwen2Model.__call__` receives a cache list, and each attention layer calls `cache.offset` for RoPE position handling and `cache.update_and_fetch(keys, values)`. The default cache created by `make_prompt_cache(model)` is one `KVCache` per transformer layer when the model does not provide `make_cache()`.

`KVCache` stores `keys`, `values`, and `offset`. Its serialized `state` is the K/V pair truncated to the current offset; its `meta_state` is empty. `save_prompt_cache()` flattens each cache state and metadata into MLX Safetensors, recording cache class names. `load_prompt_cache()` reconstructs cache objects with `from_state()` and restores their offsets from tensor shapes.

The official helper is therefore a real native-cache persistence path, subject to model/runtime fingerprint validation. It is not chat-history replay.

## Existing Ollama artifact result

The local Qwen artifact referenced by Ollama is:

```text
/Users/ashish/.ollama/models/blobs/sha256-2049f5674b1e92b4464e5729975c9689fcfbf0b0e4443ccf10b5339f370f9a54
size: 8,988,110,688 bytes
header: GGUF v3
```

The installed `mlx_lm convert` command accepts a Hugging Face model path or local Hugging Face-format directory and converts it to MLX. The installed MLX-LM package does not expose a GGUF-to-MLX input path; its GGUF module is an MLX-to-GGUF exporter. Therefore the existing Ollama GGUF cannot currently be treated as a directly consumable MLX model.

Status: **native MLX replay is technically understood, but the existing Ollama artifact is not yet a safe MLX model input.** No conversion or additional model download has been performed.

## Phase 1 model and result — 2026-08-24

Approved proof model:

```text
model: mlx-community/Qwen2.5-0.5B-Instruct-4bit
source: Hugging Face / mlx-community
format: MLX Safetensors
quantization: 4-bit, group size 64
local cache size: approximately 283 MB
```

Measured result:

```text
same-process replay: PASS
separate-process restore: PASS
wrong fingerprint rejection: PASS
prefill tokens: 36
reprocessed prefill tokens in Process B: 0
avoided prefill ratio: 1.0 for this tested capsule
cache layers: 24 KVCache objects
cache position at save: 36
cache logical bytes: 3,145,728
serialized state size: 446,668 bytes
top-1 agreement: PASS
8-token deterministic continuation agreement: PASS
```

This supports native MLX save/restore for this tested model and runtime combination only. It does not establish general Qwen, Ollama, cross-runtime, or cross-model portability.
