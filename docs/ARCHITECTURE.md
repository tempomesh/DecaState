# Architecture

The initial implementation is local-only. The current runnable path is Ollama-backed using an existing local model, with explicit metadata-only capsules. Runtime-native MLX persistence and cross-model bridges remain gated research work.

Native MLX state is now also stored as immutable checkpoint objects. Checkpoint manifests record model/runtime fingerprints, context position, lineage, provenance, and the serialized MLX-LM prompt-cache object. Rollback loads the native cache directly; it does not replay prompt history.

Fork correctness currently creates independent physical copies of a native cache. Copy-on-write and physical sharing are deliberately not claimed.

Product architecture remains broader than fork storage:

```text
DECASTATE — AI STATE RUNTIME
├── lifecycle: save / wake / checkpoint / rollback
├── sharing: fork / dedup / copy-on-write
└── portability: runtime move / model bridge / state-aware routing
```
