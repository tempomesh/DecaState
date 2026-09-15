# DecaState Architecture

**The AI State Runtime** — save, wake, fork, and honestly measure a model's
inference state. Three planes, one discipline: every claim maps to a script
and a results file.

*This is the overview; implementation-level detail (checkpoint manifests,
fingerprints, lineage, storage layout) lives in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).*

```
             YOUR APP · CODING AGENT · RAG · CI · AGENT SWARM
                                │  one line to switch
                                ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                        D E C A S T A T E                      │
  ├────────────────────┬────────────────────┬────────────────────┤
  │  STATE RUNTIME     │  HONEST GATEWAY    │  CONTEXT GUARD     │
  │  pluggable backends│  any OS · today    │  any OS · today    │
  ├────────────────────┼────────────────────┼────────────────────┤
  │ • save / wake KV   │ • byte-identical   │ • archive sessions │
  │ • checkpoint /     │   forwarding (SHA- │   raw (SHA-256)    │
  │   rollback         │   256 per request) │ • IDF-weighted     │
  │ • independent forks│ • cache HIT/MISS/  │   recall           │
  │ • byte-exact resume│   UNKNOWN states   │ • resume brief     │
  │ • wrong-model /    │ • cost from        │ • evidence index   │
  │   corruption guards│   provider usage × │                    │
  │                    │   published pricing│                    │
  └─────────┬──────────┴─────────┬──────────┴─────────┬──────────┘
            │                    │                    │
            ▼                    ▼                    ▼
    state files on disk    Anthropic / OpenAI    ~/.decastate/
    (your machine)         (provider owns the    archives → Hub
                            model + its cache)   (opt-in receipts)

  HONESTY BOUNDARY
  DecaState owns: your local state, the gateway, your measurements.
  Provider owns : the model and its cache.   Model owns: the answer.
```

## State Runtime backends

One contract — `understand → wake → fork → ask` — pluggable engines:

| Backend | Platform | Status | Proof |
|---|---|---|---|
| **MLX** (`mlx_lm`) | Apple Silicon | ✅ proven | `make phase1`, `benchmarks/results/` |
| **llama.cpp** (any GGUF) | macOS · Linux · Windows · CPU · consumer GPU | ✅ proven | `scripts/llamacpp_state_proof.py` → `benchmarks/results/llamacpp_state_proof.json` |
| vLLM / CUDA (KV connector) | server GPUs | ○ in progress | gated behind proof |
| CPU + remote/offload tiers (`push`/`pull`) | all | ○ roadmap | gated behind proof |

The llama.cpp backend drives `llama-server`'s slot save/restore API over
plain HTTP (stdlib only, no bindings). Measured on a 3.8K-token context:
after a true process kill, wake restored the state in 0.23s and the
follow-up processed **4 tokens instead of 3,772** (99.9% of re-prefill
avoided; prompt phase 26ms vs 4,200ms). State files are llama.cpp
build-sensitive — wake enforces a build+model+context fingerprint and a
SHA-256 integrity check rather than pretending files are portable.

## Honest Gateway

Runs on **your** localhost, any OS. Point `ANTHROPIC_BASE_URL` (or the
OpenAI SDK `base_url`) at it — requests are forwarded byte-identically
(SHA-256 recorded per request, streaming relayed unchanged) and every
response's provider-reported usage becomes a receipt:

- `cache_state`: **HIT / MISS / UNKNOWN** — never guessed
- `saving_state`: **verified / no_saving / not_claimed / not_priced**
- When a provider exposes no reusable cache, the answer is `not_claimed` —
  DecaState does not invent savings.

## Context Guard

A Claude Code PreCompact hook: archives the session transcript raw
(binary-exact, SHA-256), builds an evidence index, and serves IDF-weighted
recall + a resume brief. No model calls.

## What is deliberately NOT claimed (yet)

Copy-on-write storage savings · cross-runtime state migration ·
cross-model state translation · non-prefix (blended) KV reuse ·
multi-user serving. Each stays off this page until it has a script and a
results file — the same rule that makes the checked rows believable.
