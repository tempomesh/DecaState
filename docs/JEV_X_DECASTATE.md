# Jev × DecaState — What's Possible (honest assessment)

## 0. Threat check first: tailwind, not threat

Jev replaces *decision* calls (route/classify/score) — not the big-context
*understanding* calls where KV state, caching and cost live. Their own thesis
(Jevons: cheaper intelligence → orders of magnitude more calls; their Doom
demo = 10 calls/sec ≈ $7/hr) builds the world DecaState is for: **when AI
calls multiply across vendors, nobody knows what anything costs — except the
layer that measures byte-identically.**

```
                     THE COMPLEMENTARY STACK

        application state           inference state
              │                           │
              ▼                           ▼
 +---------------------+     +---------------------------+
 |   JEV (TypeSafe)    |     |   DECASTATE runtime       |
 |   fast typed        |     |   persist / wake / fork   |
 |   decisions,        |     |   the model's KV state    |
 |   70-500ms          |     |   (MLX + llama.cpp proven)|
 +----------┬----------+     +------------┬--------------+
            │  every call, every provider │
            ▼                             ▼
 +-----------------------------------------------------+
 |          DECASTATE HONEST GATEWAY (any OS)          |
 |  byte-identical forwarding · SHA-256 per request    |
 |  provider-reported usage → verifiable receipts      |
 |  HIT / MISS / UNKNOWN · never invents a saving      |
 +-----------------------------------------------------+
   State -> Questions -> Action -> VERIFY: they preach it,
   we are the State and the Verify layers of that loop.
```

## 1. The killer move — "Jev, measured" (READY)

They launched with *"extraordinary claims require receipts."* We are the
receipts company. `scripts/systemone_measure_proof.py` is committed and
dry-run validated against their real wire format:

```
 12 support tickets × 3 decisions (Choice/Score/Noul)
      ├── side A: Jev  POST /v1/systemone
      └── side B: LLM (haiku-4-5) forced to strict JSON
 measured: wall latency (median/p95) · provider-reported usage
           · cost (Jev = ANNOUNCED $0.042/MTok, labeled unverified;
                   LLM = published pricing)
           · type errors counted EMPIRICALLY on both sides
 parked:   decision quality / calibration (needs labeled data —
           recorded confidences saved for a scored pass later)
```

One command when early access lands → plausibly the **first independent
measurement of the System One claims**. Honest content either way the
numbers fall; launch-week distribution rides their wave.

## 2. Gateway support for TypeSafe as a provider (AFTER access)

Their `usage {input_tokens, output_tokens}` is normalizable today. Add
pricing + receipt support only after (a) a live response is seen and
(b) pricing appears on a real bill. Then DecaState receipts cover:
hosted LLMs · self-hosted (llama.cpp proven, vLLM next) · System One
models — one honest ledger.

## 3. Positioning line (PARKED until #1 has produced a number)

> "DecaState measures every kind of intelligence you buy — frontier LLMs,
> self-hosted models, and the new fast decision models — one honest
> receipt layer."

Rule unchanged: we publish measurements, not anticipations.

## 4. Jev *inside* DecaState — mostly NO (and why that's the brand)

```
 tempting spot                      verdict
 ------------------------------    ------------------------------------
 Guard recall candidate scoring    NO — sends user context to a third
                                   party; breaks "your data never leaves
                                   your machine except to YOUR provider"
 Hub receipt anomaly scoring       overkill — rate limits + validation
                                   already do the job at zero privacy cost
 gateway routing decisions         maybe LATER, opt-in and labeled, if we
                                   ever ship routing at all
```

The trust layer stays vendor-free. That refusal *is* the product.

## 5. What we deliberately do NOT do

- No re-architecting around an early-access, single-vendor API.
- No repeating "can't hallucinate" (typed ≠ correct) or "100×" (their
  harness) in our copy — we cite only what our own harness measured.

## 6. Sequence

```
 NOW      user: join TypeSafe waitlist          (only blocker)
 DAY 0    run systemone_measure_proof.py        (one command)
 DAY 0+1  publish "System One, independently measured" — savings page
          + launch content; THEN unpark §3 and evaluate §2
 LATER    scored calibration pass (labeled data) if the story earns it
```
