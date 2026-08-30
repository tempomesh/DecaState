# API savings, explained honestly (Reddit / HN / LinkedIn kit)

The audiences that make things viral (r/LocalLLaMA, HN) will test every claim.
This kit only contains claims backed by `benchmarks/results/api_added_savings.json`
(real billed requests, rerunnable via `scripts/api_added_savings_proof.py`).

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
