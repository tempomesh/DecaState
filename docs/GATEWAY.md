# DecaState API Gateway

## Implementation status (2026-09-03)

```text
Anthropic gateway + cache injection       IMPLEMENTED
Anthropic provider usage audit            IMPLEMENTED
Claude Code API-key routing               EXPERIMENTAL / measurable
Claude Code Context Guard                 IMPLEMENTED separately
Incremental streaming passthrough        IMPLEMENTED (SSE relayed byte-for-byte, usage captured)
Total invoice accounting                  IMPLEMENTED (decastate audit — input+cache+output)
OpenAI API adapter                        IMPLEMENTED (auto-detected usage; verified on gpt-4o-mini)
Shareable receipt card                    IMPLEMENTED (decastate brag — zero-dep SVG)
ChatGPT/Codex subscription interception   NOT POSSIBLE from this gateway
```

The current gateway is therefore a working **Anthropic API measurement and
cache-injection prototype**, not yet a universal Claude/OpenAI production
proxy. The next gateway milestone is streaming passthrough and end-to-end
Claude Code API-key testing. The OpenAI adapter is a separate implementation
because OpenAI has a different request schema and reports cached usage in a
different usage structure.

An **honest transparent proxy** for the Anthropic Messages API. It sits between your
coding agent (e.g. Claude Code) and the provider, and does exactly four things:

1. **Forwards the request body byte-for-byte** to the upstream provider.
2. **Proves it** with SHA-256 integrity hashes — the whole body, plus the `system`,
   `tools`, and `messages` components hashed separately.
3. **Reads the provider's own usage fields** from the response:
   `cache_creation_input_tokens`, `cache_read_input_tokens`, `input_tokens`,
   `output_tokens`.
4. **Records an audit line and prints a report.**

## What it deliberately does NOT do

It never summarizes, drops files, rewrites user instructions, or alters tool schemas
or tool order. The model sees exactly what your agent sent. The `X-DecaState-Integrity`
response header and the per-request `prompt_integrity: unchanged` field are the proof.

## Attribution — read this before quoting a number

The saving reported is the **provider's prompt cache** (Anthropic's, in this case).
DecaState **measures and protects** that cache; it does **not** create it. Claude Code
already uses Anthropic prompt caching on its own, so a transparent gateway does not by
itself turn a cache "miss" into a "hit" for Claude Code — its honest value here is:

- **measurement** — surfacing your real cache-read vs cache-creation token split, and
- **integrity** — proving the forwarded prompt was not altered.

For clients that do **not** already cache, the opt-in `--inject-cache` mode adds a
`cache_control` breakpoint (model-visible content is never altered; the report says
`content-unchanged (cache_control injected)` instead of `unchanged`). **Measured result
(2026-08-30, real billed requests, claude-haiku-4-5, ~13K-token prefix):** a non-caching
client paid $0.026070 input for a 2-request pair direct; through `--inject-cache` it paid
$0.017606 — **DecaState added a 32.5% input saving**, and every further same-prefix
request within the TTL saves ~90% of the prefix. Evidence:
`benchmarks/results/api_added_savings.json` (`scripts/api_added_savings_proof.py`).

**OpenAI:** caching is automatic — no Anthropic gateway can add hits there. The
repository contains a direct OpenAI cache-observation probe, but there is no
OpenAI-compatible DecaState proxy yet. On OpenAI, the planned adapter's first
job is measurement: cached tokens, stable-prefix changes, and actual cost.

The `$` figures are **illustrations**: provider-reported cached tokens × published
per-model input pricing (cache read ≈ 0.1×, cache write ≈ 1.25×). They are not a bill.
Provider cache is also **ephemeral** (~5-minute default TTL, 1h option), so savings
only accrue while requests stay inside that window; each read refreshes the clock.

## Run it

```bash
source .venv/bin/activate

# 1. Verify the plumbing (no provider, no key needed) — proves byte-identical
#    forwarding + usage extraction against a local echo upstream.
decastate gateway-selftest

# 2. Run the real gateway in front of the real provider.
decastate gateway --port 8799
```

Point your agent at it (needs your own API key — a subscription won't expose usage):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_BASE_URL="http://127.0.0.1:8799"
claude
```

Every request prints a report and appends one JSON line to
`~/.decastate/gateway/audit.jsonl`. Endpoints: `GET /healthz`, `GET /audit`
(last 50 records, used by the local dashboard).

## Prove savings honestly (the A/B test)

Run the **same** coding task twice and compare `cache_read_input_tokens`:

- **A** — Claude Code → Anthropic direct
- **B** — Claude Code → DecaState gateway → Anthropic

Honest expected outcome for Claude Code: **A ≈ B**, because Claude Code already caches.
If B shows *more* cache reads than A, that is a real measured win — publish it. If they
match, DecaState's value is the report and the integrity guarantee, and the claim must
say exactly that.

## Claude Code integration boundary

There are two separate DecaState features:

```text
Claude Code PreCompact hook
    → Context Guard archives the local transcript before compaction
    → no provider request is intercepted

Claude Code with an Anthropic API key
    → ANTHROPIC_BASE_URL points to the local gateway
    → gateway forwards the API request and records provider usage
```

Context Guard protects recoverability of the local transcript. The API gateway
measures Anthropic's server-side prompt-cache usage. Neither feature can read,
export, or move Anthropic's internal KV tensors, and neither applies to a
ChatGPT-authenticated Claude/Codex subscription session.

The current proxy buffers the upstream response before returning it. It is
appropriate for controlled measurements, but streaming passthrough is required
before recommending it as a daily Claude Code replacement.

## Remaining production work

Before calling this a production gateway, DecaState still needs:

- incremental SSE streaming with unchanged event ordering;
- an OpenAI adapter for API-key-backed applications and Codex API clients;
- provider-specific cost calculators including output, reasoning, and tool charges;
- automated cache-miss diagnostics and repeated-workload A/B tests;
- secret redaction, request limits, retry policy, structured error handling, and
  stronger integration tests.
