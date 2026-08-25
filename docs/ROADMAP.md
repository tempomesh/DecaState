# Roadmap

Follow the phase gates in `DECASTATE_CODEX_COMPLETE_BUILD_PLAN.md`. The initial persistence and branching gates have passed for the tested MLX/Qwen configuration.

Current status:

```text
Phase 1  native MLX save/wake              PASS
Phase 2  checkpoint/rollback                PASS
Phase 3  physical-copy fork correctness    PASS
Phase 3b coding-agent product demo          PASS
Investor MVP native lifecycle                PASS
Phase 4  copy-on-write research             NEXT
Phase 5  same-model cross-runtime           FUTURE
Phase 6  cross-model translation             FUTURE
```

The next exact task is to investigate physical versus logical sharing for forked native state. No COW or portability claim is allowed until measured.

Run the storage experiment with:

```bash
make cow-benchmark
```

This measures an APFS/file clone primitive over a real MLX cache. It does not yet integrate COW into native checkpoint or fork behavior.
