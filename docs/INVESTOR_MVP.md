# Investor MVP

## What exists today

DecaState is an AI State Runtime prototype with a working native MLX lifecycle:

```text
create state → continue state → checkpoint → rollback → fork physical branches → wake exact continuation
```

The lifecycle has been exercised with real repository context and the tested Qwen MLX model.

## Investor demo

```bash
source .venv/bin/activate
make public-demo
```

The public demo shows repository understanding, checkpointing, native wake, and coder/reviewer/security branches. The direct CLI lifecycle is available for live demonstrations with `decastate create`, `continue`, `checkpoint`, `rollback`, `fork`, and `status`.

## Evidence

- Exact cold-vs-wake continuation at 128, 512, 1,024, and 2,048 tokens.
- Exact checkpoint/rollback continuation at the same lengths.
- Exact wake for three independent physical-copy branches from a 1,024-token base.
- Wrong model, missing checkpoint, and corrupt checkpoint rejection.
- No original-prefix prefill after native restore in the tested workflows.

## Honest boundary

The current MVP is local and MLX-specific. It does not yet provide production HA, cloud storage, runtime migration, model migration, or proven copy-on-write storage savings. Those are the expansion path for the AI State Runtime.

The deployable supported scope is documented in [Operations](OPERATIONS.md). This is a single-node production MVP, not yet a distributed production platform.

Release: `0.1.0`.
