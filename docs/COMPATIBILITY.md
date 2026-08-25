# Compatibility

No runtime or model compatibility is claimed until tested and recorded.

Verified:

| Source | Target | Capability | Evidence |
|---|---|---|---|
| Qwen2.5-0.5B MLX | same MLX process | native replay | Phase 1 PASS |
| Qwen2.5-0.5B MLX | new MLX process | save/restore | Phase 1 PASS |
| Qwen2.5-0.5B MLX | native checkpoint | checkpoint/rollback | Phase 2 PASS |
| Qwen2.5-0.5B MLX | physical fork | independent branches | Phase 3 PASS |

Not verified: Ollama native-state restore, MLX↔Ollama state transfer, llama.cpp, vLLM, cross-model translation, and native KV copy-on-write sharing. An APFS file-clone experiment succeeded, but did not demonstrate measurable physical storage savings.
