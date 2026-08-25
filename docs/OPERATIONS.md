# Production Operations

The current production MVP is a single-node macOS Apple Silicon runtime using the project `.venv`, MLX-LM, and local filesystem state. It is not yet a cloud service or multi-node HA product.

State is stored under `DECASTATE_HOME` when set, otherwise `~/.decastate`.

Safety properties:

- State writes use temporary files followed by atomic replacement.
- Native state files carry SHA-256 integrity metadata.
- Per-state advisory locks serialize mutating operations.
- Checkpoints are immutable and cannot be overwritten.
- Model fingerprints are validated before restore.
- Native state never goes into Git by default.

Back up the complete `DECASTATE_HOME` directory, including `states/`, `checkpoints/`, and `branches/`. If integrity validation fails, preserve the affected state and restore the last known-good immutable checkpoint.

MLX may use the Apple GPU while a model operation is active. DecaState does not run a background daemon in the current MVP. Stop Ollama separately when required with `ollama stop <model>`.

Not production-supported yet: multi-node HA, remote state storage, encryption at rest, RBAC, audit logging, runtime migration, model migration, and COW savings.
