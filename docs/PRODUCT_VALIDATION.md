# Product Validation

## Current demo

Run:

```bash
make demo
```

The demo uses real DecaState source files, a real MLX model, native cache checkpoints, and physical-copy branches. It demonstrates the user-facing story:

```text
Understand repository once
        ↓
Checkpoint repo-understood
        ↓
Fork coder / reviewer / security
        ↓
Wake and continue each branch
```

## Questions for the first developer users

1. How often does your coding agent rebuild the same repository context after a restart?
2. Would checkpointing and branching one understood repository state change your workflow?
3. Is the valuable outcome lower restart latency, cheaper parallel agents, reproducibility, or something else?

## Validation boundary

The current implementation proves native MLX persistence and physical-copy branching for the tested model. It does not yet prove COW savings, cross-runtime movement, or cross-model switching.
