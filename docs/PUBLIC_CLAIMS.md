# Public Claims

## Supported

For the tested MLX/Qwen configuration, DecaState has measured:

- native save/wake across separate processes;
- exact deterministic continuation after restore;
- checkpoint/rollback with lineage and fingerprint guards;
- physical-copy fork correctness;
- a real coding-agent repository-context demo.

## Not supported or not yet proven

- universal model support;
- Ollama native-state restore;
- COW storage savings;
- llama.cpp or vLLM migration;
- cross-model state translation;
- cloud state storage;
- production reliability or cost guarantees.

## Product definition

DecaState remains the AI State Runtime. Lifecycle, sharing, and portability are the three product dimensions:

```text
LIFECYCLE       save / wake / checkpoint / rollback
SHARING         fork / dedup / copy-on-write
PORTABILITY     runtime move / model bridge / state-aware routing
```
