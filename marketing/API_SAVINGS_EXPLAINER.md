# API savings, explained honestly (Reddit / HN / LinkedIn kit)

The audiences that make things viral (r/LocalLLaMA, HN) will test every claim.
This kit separates measured results from illustrative calculations. Measured
claims point to a result artifact and rerunnable script; illustrative examples
are explicitly labelled and are not product benchmarks.

## The real measured Claude API result

DecaState has measured this with real Anthropic API requests, not simulated
latency or an assumed cache hit:

| Test | Direct Anthropic | Through DecaState | Result |
|---|---:|---:|---:|
| 2-request pair, non-caching client | $0.026070 | $0.017606 | **32.5% lower input cost** |
| 10-request session, non-caching client | $0.137822 | $0.029735 | **78.4% lower input cost** |

The 10-request result used `claude-haiku-4-5`, one repeated repository prefix,
ten different instructions, and Anthropic-reported usage fields. It measures
**input-token cost**, not the entire invoice. Output tokens, tool charges,
compaction calls, and any retrieval calls must also be included before claiming
total API-bill savings.

Reproduce it with:

```bash
cd /Users/ashish/DECASTATE
source .venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-..."
decastate gateway --port 8801 --inject-cache
```

In another terminal:

```bash
cd /Users/ashish/DECASTATE
source .venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-..."
export GATEWAY_URL="http://127.0.0.1:8801"
.venv/bin/python scripts/api_session_savings_proof.py
```

Evidence: `benchmarks/results/api_session_savings.json`.

### What the Claude number means

```text
same stable context
        │
        ├── request 1: cache write (slightly more expensive)
        ├── request 2: cache read (much cheaper)
        ├── request 3: cache read
        └── ... within the provider cache lifetime
```

This is provider-native prompt caching. DecaState does **not** receive or
control Anthropic's internal KV tensors. It adds the cache opt-in for clients
that omitted it, forwards the request, and records the provider's reported
usage. If Claude Code already set the cache marker, DecaState may add no new
discount; it can still provide measurement and auditability.

## Claude hero models: the same illustration on Anthropic pricing

Same workload as the OpenAI example below — one 100,000-token project prompt sent
ten times, 1,000 output tokens per request, Anthropic's published rates (cache
read ≈ 0.1× input, cache write ≈ 1.25×, 5-min TTL refreshed per read). This is a
**calculation**, not a measured DecaState benchmark (the measured ones are above).

| Model | Input / 1M | Cached read / 1M | Output / 1M | 10 req without cache | 10 req with cache | Illustrative saving |
|---|---:|---:|---:|---:|---:|---:|
| Claude Fable 5 | $10.00 | $1.00 | $50.00 | $10.500 | $2.650 | **74.8%** |
| Claude Opus 5 | $5.00 | $0.50 | $25.00 | $5.250 | $1.325 | **74.8%** |
| Claude Sonnet 5 | $2.00 | $0.20 | $10.00 | $2.100 | $0.530 | **74.8%** |
| Claude Haiku 4.5 | $1.00 | $0.10 | $5.00 | $1.050 | $0.265 | **74.8%** |

Worked example (Sonnet 5): without = 10×100k×$2/1M + 10×1k×$10/1M = $2.10; with =
100k×$2.50/1M (write) + 9×100k×$0.20/1M (reads) + $0.10 output = $0.53.

The percentage is identical across tiers because Anthropic's cache multipliers
(0.1× / 1.25×) are uniform — but the **dollar** saving scales with the tier:
the same workload saves ~$0.79 on Haiku and ~$7.85 on Fable 5. Note the
measured 78.4% above beat this 74.8% illustration because the measured run had
near-zero output tokens; output cost dilutes the percentage, never the input
mechanism. (Fable 5.1 appears in newer Claude Code builds; its pricing isn't in
our verified table, so it's deliberately excluded rather than guessed.)

## GPT-5.6 Luna, Terra, and Sol: clear example, not yet a DecaState benchmark

The following is a calculation using one 100,000-token project prompt sent ten
times, with 1,000 output tokens per request. It illustrates the economics of
OpenAI's automatic prompt caching; it is **not** a measured DecaState result.

| Model | Normal input / 1M | Cached input / 1M | Output / 1M | 10 requests without cache | 10 requests with cache | Illustrative saving |
|---|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | $4.00 | $0.40 | $20.00 | $4.200 | $1.060 | **74.8%** |
| GPT-5.6 Terra | $2.00 | $0.20 | $12.00 | $2.120 | $0.550 | **74.1%** |
| GPT-5.6 Luna | $0.20 | $0.02 | $1.20 | $0.212 | $0.055 | **74.1%** |

Calculation for Luna:

```text
Without cache:
  input  = 100,000 × $0.20 × 10 / 1,000,000 = $0.200
  output =   1,000 × $1.20 × 10 / 1,000,000 = $0.012
  total  = $0.212

With cache:
  first write = 100,000 × $0.20 × 1.25 / 1,000,000 = $0.025
  nine reads  = 900,000 × $0.02 / 1,000,000       = $0.018
  output      = $0.012
  total       = $0.055
```

### How savings scale as requests grow

Using the same Luna example, the first request pays for the cache write and
later requests pay the cheaper cached-input rate:

| Requests | Without cache | With cache | Saved | Saving |
|---:|---:|---:|---:|---:|
| 2 | $0.0424 | $0.0294 | $0.0130 | **30.7%** |
| 10 | $0.2120 | $0.0550 | $0.1570 | **74.1%** |
| 100 | $2.1200 | $0.3430 | $1.7770 | **83.8%** |
| 1,000 | $21.2000 | $3.2230 | $17.9770 | **84.8%** |

```text
2 requests      without ████████████████████  $0.0424
                with    ██████████████        $0.0294

10 requests     without ████████████████████  $0.2120
                with    █████                 $0.0550

100 requests    without ████████████████████  $2.1200
                with    ███                   $0.3430

1,000 requests  without ████████████████████  $21.2000
                with    ███                   $3.2230
```

The dollar saving keeps growing because each additional request reuses the
stable prefix. The percentage rises more slowly and approaches the provider's
cached-input economics; it is not guaranteed if the prefix changes or the
provider cache expires. This table includes output cost but assumes the same
1,000 output tokens per request, so it is an example rather than a production
forecast.

OpenAI reports cached-token usage in the API response. A DecaState OpenAI
adapter should measure `input_tokens`, `input_tokens_details.cached_tokens`,
`cache_write_tokens`, `output_tokens`, and reasoning tokens where available,
then calculate the actual request total. OpenAI's current model pricing is in
the [official model comparison](https://developers.openai.com/api/docs/models/compare).

Because OpenAI already caches automatically, DecaState should not promise an
additional discount until a real OpenAI API A/B test proves one. The immediate
OpenAI product is cache observability: which tokens were cached, which were
not, why the prefix changed, and what the provider actually charged.

## Two real integration architectures

The user experience is similar, but the provider mechanisms differ:

### Claude API / Claude Code with an API key

```text
USER PROMPT
    │
    ▼
Claude Code or your application
    │  ANTHROPIC_BASE_URL points locally
    ▼
DECASTATE ANTHROPIC GATEWAY
    │  hash request
    │  preserve content
    │  add cache marker only when needed
    │  log usage and cost
    ▼  encrypted HTTPS over the internet
ANTHROPIC API
    │
    │  Anthropic owns the server-side prompt cache/KV state
    │  DecaState cannot read those tensors
    ▼
CLAUDE RESPONSE
    │
    ▼
Claude Code / application
```

### OpenAI API / API-key-backed coding client

```text
USER PROMPT
    │
    ▼
Codex API client or your application
    │  OpenAI-compatible base URL, when supported
    ▼
DECASTATE OPENAI ADAPTER
    │  preserve request
    │  keep stable prefix stable
    │  log hashes, cached tokens, cost, misses
    ▼  encrypted HTTPS over the internet
OPENAI API
    │
    │  OpenAI automatically checks its server-side prompt cache/KV state
    │  DecaState cannot read or move that provider KV state
    ▼
GPT-5.6 Luna / Terra / Sol response
    │
    ▼
Codex API client / application
```

**Current gateway limitation (stated so nobody discovers it for us):** the gateway
buffers upstream responses; it does not yet relay SSE streams incrementally. For
Claude Code that means responses appear only when complete — fine for measurement
sessions and the audit trail, not yet a daily driver. Streaming passthrough is the
next gateway milestone.

The important boundary is:

```text
DecaState owns:       request routing, hashes, evidence, metrics, policy
Provider owns:        model execution and server-side KV/prompt cache
Model owns:           reasoning and the final answer
```

The Codex model selector shown in the desktop app is not, by itself, an API
gateway connection. A ChatGPT/Codex subscription session is managed by OpenAI;
DecaState cannot intercept it or claim direct quota savings. An API-key-backed
client is the testable integration surface.

---

## Reddit / HN post (technical, self-aware, no hype)

**Title options:**
- I measured what LLM prompt caching actually saves — and when a proxy can/can't help
- Anthropic's cache discount is opt-in and many clients never opt in. So I built an honest gateway.
- Show HN: DecaState — byte-identical LLM gateway that proves (with hashes) it didn't touch your prompt

**Body:**

Your coding agent resends the same repo context with every request. Both big
providers discount repeated context — but differently, and the difference is
exactly where a tool can or can't help:

```text
ANTHROPIC — discount is OPT-IN (cache_control on the stable prefix)

  no cache_control:   req1  13,036 tok @ full     req2  13,034 tok @ full   ← again
  with it (injected): req1  13,021 @ 1.25× write  req2  13,021 @ 0.1× read  ← 90% off prefix

OPENAI — discount is AUTOMATIC (≥1024-token prefixes, ~50% off)

  req1  cached: 0        req2  cached: 10,880   ← OpenAI did this by itself
```

I measured it with real billed requests (numbers in the repo):

- **Anthropic, non-caching client, 2-request pair:** $0.026070 direct vs $0.017606
  through my gateway with `--inject-cache` → **32.5% saved**, and every further
  same-prefix request inside the ~5-min TTL saves ~90% of the prefix.
- **Anthropic, client that already caches (e.g. Claude Code):** the gateway adds
  **~0** — the discount was already happening. It measures and verifies instead.
- **OpenAI:** request 2 reused 10,880 cached tokens automatically. No proxy can
  add anything there. Any tool claiming OpenAI cache savings is selling you
  OpenAI's own feature.

What the gateway actually guarantees (this part IS mine to claim):

- forwards byte-identically by default — SHA-256 of body/system/tools/messages,
  per request, in an audit log; the inject mode changes ONLY the cache annotation
  and reports "content-unchanged (cache_control injected)" instead of "unchanged"
- never summarizes, drops files, rewrites prompts, or reorders tools
- reads the PROVIDER's usage fields — no timing guesswork
- `decastate savings` prints your running total (cached tokens reused, est. $)

Local-first is the actual core of the project (persist/fork real MLX KV state,
survive process death, 0 tokens re-read — different mechanism, no bill involved).
The gateway is the API-side companion. MIT, repo has every script + result JSON.

**Prepared first comment (post it yourself under the thread):**

> Scope notes before anyone asks: (1) Anthropic cache TTL is ~5 min (refreshes on
> each read) — savings accrue within active sessions, this is not "cache your repo
> overnight". (2) The 32.5% figure is a 2-request pair; the asymptote per extra
> request is ~90% of the prefix. (3) If your client already sets cache_control,
> this adds nothing — that's why the default mode is measurement, and injection
> is an explicit flag. (4) $ figures are provider-reported tokens × published
> pricing.

---

## LinkedIn Variant E — the API-savings explainer (pairs with the ASCII diagram image)

Did you know both Anthropic and OpenAI give discounts on repeated context — but
most people only get one of them?

Your AI coding agent resends your repo context with EVERY request. That's the
biggest line on your inference bill.

→ OpenAI discounts repeats automatically (~50% off cached tokens). You're covered.
→ Anthropic discounts repeats 90% — but ONLY if your client asks (cache_control).
   Many raw scripts and custom agents never ask. They pay full price, every time.

I measured it with real billed requests:

• Non-caching client, direct: $0.0261 for a 2-request pair
• Same client through DecaState's gateway (it adds the annotation, touches
  NOTHING else — proven with SHA-256 hashes per request): $0.0176
• That's 32.5% saved on 2 requests — and ~90% off the repeated context on every
  request after that.

And the honest part, because smart readers will check:
✗ If your client already caches (Claude Code does), DecaState adds ~0 — it
  measures and verifies instead.
✗ On OpenAI, nobody can add savings — caching is automatic. We just show you
  the number the provider reports.

Every claim maps to a script and a results file in the repo. MIT licensed.

⭐ github.com/tempomesh/DecaState

#AI #LLM #DeveloperTools #OpenSource #CostOptimization

---

## The one-table cheat sheet (drop into any thread)

| | Anthropic | OpenAI |
|---|---|---|
| Discount on repeated context | 90% off cached reads | ~50% off cached reads |
| Activation | opt-in (`cache_control`) | automatic (≥1024 tok) |
| Who misses it | raw scripts, custom agents | ~nobody |
| DecaState adds | +32.5% measured (2 reqs); ~90%/req after | nothing — measures only |
| DecaState guarantees | byte-identical forward, SHA-256 audit | same |

---

## HOW DecaState does it — mechanism diagrams (for posts, decks, README)

### The core mechanic: DecaState "asks" for the discount your client forgot

```text
 YOUR AGENT                DECASTATE GATEWAY                  ANTHROPIC API
     │                      (localhost, yours)                      │
     ├─► request ──────────► 1. SHA-256 everything                  │
     │   (repo context,      2. already has cache_control?          │
     │    no cache_control)     YES → touch nothing, measure        │
     │                          NO  → add ONE annotation:           │
     │                               cache_control: ephemeral       │
     │                               (model sees identical words)   │
     │                       3. forward ──────────────────────────► │ bills repeated
     │                       4. read usage.cache_read ◄──────────── │ prefix at 0.1×
     │ ◄── response ─────────5. log → audit.jsonl                   │
     │     (untouched)          `decastate savings` = running total │
```

### Before / after billing

```text
 WITHOUT DECASTATE                        WITH DECASTATE (--inject-cache)
 req 1  ████████████ 13,036 @ full        req 1  ████████████ 13,021 @ 1.25× (once)
 req 2  ████████████ 13,034 @ full        req 2  ▌13,021 @ 0.1×  ◄── 90% off
 req N  ████████████ full AGAIN           req N  ▌~90% off, every time (within TTL)

 real 2-request bills:  $0.026070  →  $0.017606  =  32.5% SAVED (grows per request)
```

### Why the number is trustworthy

```text
 sha256(what you sent) ──┐
                         ├── MUST MATCH (or the cache_control-only diff is DECLARED)
 sha256(what API got) ───┘
 savings = the PROVIDER's usage fields, never timing guesses
 every request = one replayable line in audit.jsonl
```

### The whole story (hero shot)

```text
                    ◈  D E C A S T A T E
                 "pay for understanding ONCE"
                             │
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
   LOCAL RUNTIME (core)                 API GATEWAY (companion)
   save real KV state → disk            inject the cache opt-in
   kill / reboot / fork                 clients forget to claim
   wake byte-exact, 0 re-read           90% off repeated context
   13.7× faster resume                  +32.5% measured (2 reqs)
          └──────────────────┬──────────────────┘
                             ▼
             same context, never paid for twice
```

---

## Show HN: Context Guard (the second post, once Guard ships publicly)

**Title:** Show HN: I got tired of Claude Code's compaction eating my session, so my sessions checkpoint themselves now

**Body:**

When Claude Code's context fills up, it summarizes your history — and exact
numbers, tool outputs, and decisions from mid-session can degrade or vanish.

Context Guard hooks Claude Code's PreCompact event and, before every compaction:
archives the full raw transcript (hashed, local-only), builds a structured
checkpoint (goals / files / commands / test signals), and keeps the full raw
archive alongside a searchable evidence index. Later:
`decastate guard-recall "<query>"` returns the matching original record with
timestamp provenance — not a summary of a summary.

The design rule that matters: **Guard never summarizes.** No model calls. The
raw archive is the source of truth; the checkpoint is a map. A tool that fixes
lossy summarization with more summarization would be selling the disease as
the cure.

Dogfood numbers (run on the actual session that built the feature): 9.9 MB /
2,272-record transcript → 801 verbatim evidence entries, checkpointed in 0.052s;
recall retrieved exact file contents from day 1 of a week-long session, past
every compaction in between.

What it does NOT do (so you don't have to ask): can't prevent compaction,
can't touch Anthropic's server-side KV cache, can't measure subscription
dollars. Whether checkpoint+recall beats default compaction on quality/tokens
is pre-registered as an A/B in the repo — results get published either way,
including if default compaction wins.

MIT. Local files only. Part of DecaState (an AI State Runtime — same philosophy
at the API level: measured, hash-proven, no invented numbers).
