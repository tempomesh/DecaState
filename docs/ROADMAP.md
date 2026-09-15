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

API/context product tracks are separate from the native MLX lifecycle gates:

```text
Context Guard raw archive + recall         PASS (Claude Code hook; local-only)
Anthropic cache gateway                    PASS (prototype; measured input cost)
Claude Code API-key end-to-end accounting  NEXT
Gateway streaming passthrough              NEXT
OpenAI/Codex API adapter                   FUTURE
Total provider invoice accounting          FUTURE
Cloud/auth/multi-user deployment           FUTURE
```

The Anthropic gateway exists today. The OpenAI gateway does not yet exist;
OpenAI's automatic prompt caching means its first useful version should measure
and explain cache hits rather than promise an additional discount. The Codex
model picker in the desktop app is not an API gateway connection, so a
ChatGPT-authenticated Codex session is outside the current interception scope.

The next exact task is to investigate physical versus logical sharing for forked native state. No COW or portability claim is allowed until measured.

For the API product track, the next exact task is to add streaming-safe
Anthropic routing and run a real Claude Code API-key A/B test. Only after that
should an OpenAI-compatible adapter be implemented and tested against
`gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`.

Run the storage experiment with:

```bash
make cow-benchmark
```

This measures an APFS/file clone primitive over a real MLX cache. It does not yet integrate COW into native checkpoint or fork behavior.
