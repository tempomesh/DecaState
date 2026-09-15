# Forge / moltenML: How the Real System Uses Everything You Just Learned

This guide continues your transformer study (`01_foundations.md` and
`transformer-architecture-guide_claude.md`) and connects it to Forge — the real
system running on your Macs. Same style: plain language first, ASCII pictures,
then the technical name.

The bridge in one sentence: **you learned that a model is a 24-floor building;
Forge is what happens when the building is too big for one Mac, so the floors
are shared across several Macs — and everything else (checkpoints, KV cache,
flywheel) exists to keep that shared building safe, fast, and improving.**

No claim here is invented: every mechanism below is the one actually running
in `grid/foreman.py`, `grid/agent.py`, `grid/pipetrain.py`, `grid/fuse.py`,
and `grid/serve.py`, proven live on an M4 Max + M4 + M5 fleet.

---

## Table of Contents

1. [The one-picture connection](#1-the-one-picture-connection)
2. [The Fleet and the Coordinator](#2-the-fleet-and-the-coordinator)
3. [Model split: where the knife cuts](#3-model-split-where-the-knife-cuts)
4. [One training step across 3 Macs](#4-one-training-step-across-3-macs)
5. [LoRA: why small Macs can train big models](#5-lora-why-small-macs-can-train-big-models)
6. [Checkpoints: what is saved, where, and the all-or-nothing rule](#6-checkpoints)
7. [Failover: a Mac closes its lid](#7-failover-a-mac-closes-its-lid)
8. [Fuse: welding the pieces back into one model](#8-fuse-welding-the-pieces-back-into-one-model)
9. [Inference in Forge: serving and the decode loop](#9-inference-in-forge)
10. [Prefill, KV cache, and the Memory Bus](#10-prefill-kv-cache-and-the-memory-bus)
11. [Model Store: download once, share over the LAN](#11-model-store)
12. [The Flywheel: how the model gets smarter every night](#12-the-flywheel)
13. [Evals: proof, not vibes](#13-evals-proof-not-vibes)
14. [The Router: cheapest model that fits](#14-the-router)
15. [Common language → technical name](#15-common-language--technical-name)
16. [Quick reference](#16-quick-reference)

---

## 1. The one-picture connection

Your foundations doc ends with this picture: a model is a 24-floor building,
each floor = attention room + MLP room + a K/V rack.

Forge's starting problem:

```text
THE BUILDING IS TOO HEAVY FOR ONE MAC

Qwen2.5-0.5B = 24 floors          One 16 GB MacBook:
+ embedding foundation             "I can hold a few floors,
+ output roof                       not the whole building."
```

Forge's answer: keep the building EXACTLY as you learned it — same floors,
same rooms, same order — but let three Macs each hold a STRETCH of floors:

```text
              THE SAME 24-FLOOR BUILDING, SHARED BY 3 MACS
              (real split from a live Forge run)

                          ROOF: output weights → next token
                        ┌────────────────────────────┐
                        │ FLOOR 22 … FLOOR 23        │   MAC 3: "M5"
                        │ attention + MLP each       │   holds floors 22–23
                        │ + output head              │   + the roof
                        └─────────────▲──────────────┘
                                      │  hidden vectors travel
                        ┌─────────────┴──────────────┐
                        │ FLOOR 20 … FLOOR 21        │   MAC 2: "M4"
                        │ attention + MLP each       │   holds floors 20–21
                        └─────────────▲──────────────┘
                                      │  hidden vectors travel
                        ┌─────────────┴──────────────┐
                        │ FLOOR 0 … FLOOR 19         │   MAC 1: "M4 Max"
                        │ attention + MLP each       │   holds floors 0–19
                        │ + EMBEDDING FOUNDATION     │   (the biggest Mac
                        └────────────────────────────┘    takes the most)
                                      ▲
                       FOUNDATION: BOS, I, like, tea → vectors
```

Nothing about a floor changes. What changes is only **which machine the floor
lives on**, and that the hidden vectors must now travel **over the network**
between Macs instead of staying inside one machine's memory.

```text
common language:   three small buildings acting as one tall one
technical name:    pipeline parallelism (pipeline-parallel training/inference)
```

---

## 2. The Fleet and the Coordinator

Before any splitting, Forge needs to know which Macs exist and who assigns
work.

```text
                        THE COORDINATOR ("foreman")
                        one small server, the manager
                     it holds NO model and does NO math
                                   ▲  ▲  ▲
              every 5 seconds      │  │  │      every 5 seconds
           "I'm here, I have       │  │  │   "I'm here, 3.4 GB free"
            31 GB free"            │  │  │
                 ┌─────────────────┘  │  └──────────────────┐
                 │                    │                     │
          ┌──────┴──────┐      ┌──────┴──────┐       ┌──────┴──────┐
          │  M4 Max     │      │  M4         │       │  M5         │
          │  agent.py   │      │  agent.py   │       │  agent.py   │
          └─────────────┘      └─────────────┘       └─────────────┘
```

Three rules that matter:

```text
1. HEARTBEAT   Every Mac "checks in" every 5 seconds with its free memory.
               Silence for ~40 seconds = the Mac is considered gone.

2. PULL, NOT PUSH   The coordinator NEVER connects into a Mac.
               When a Mac checks in, the reply may contain:
               "here is your piece of a job." The Mac pulls its own work.

3. APPROVAL    A new Mac is PENDING until a human approves it.
               Unapproved machines never receive work.
```

```text
common language:   the manager with a clipboard; workers come ask for tasks
technical name:    control plane (coordinator) + agents; heartbeat protocol
```

---

## 3. Model split: where the knife cuts

This is your question: when the model is split, what happens to attention,
residual, normalization, and MLP?

Answer: **the knife only ever cuts BETWEEN floors, never inside a floor.**
Each floor travels as a complete unit — its attention room, both residual
pipes, both normalization stations, and its MLP room stay together.

```text
        WHERE THE KNIFE IS ALLOWED TO CUT

        FLOOR 21   ┌─────────────────────────────┐
                   │ norm → Q/K/V attention      │
                   │      → residual add         │      ← the whole floor
                   │      → norm → MLP           │        stays together
                   │      → residual add         │
                   └─────────────────────────────┘
   CUT HERE ✂ ────────────────────────────────────────  between floors: OK
        FLOOR 20   ┌─────────────────────────────┐
                   │ norm → Q/K/V attention      │
                   │      → residual add         │
                   │      → norm → MLP           │
                   └─────────────────────────────┘

   NEVER  ✂  through the middle of attention, or between
             attention and its residual, or inside the MLP.
```

Why cutting between floors is safe: the ONLY thing a floor hands to the floor
above is one package of hidden vectors. That is a clean doorway. Inside a
floor, attention/residual/norm/MLP constantly share intermediate values — no
clean doorway exists there.

```text
      WHAT ACTUALLY CROSSES THE NETWORK BETWEEN TWO MACS

      Mac 1, top of floor 19
             │
             │   hidden vectors for the tokens
             │   (just a block of numbers, a few MB)
             ▼
      ══════ network (WebSocket relay) ══════
             │
             ▼
      Mac 2, bottom of floor 20
```

How Forge decides who gets which floors:

```text
1. Count each Mac's SPARE memory (never the whole machine —
   the owner keeps working).

2. The BIGGEST Mac gets the INPUT end, because the input end
   includes the EMBEDDING TABLE — the single heaviest object
   in the model (vocab size × vector size).

3. Remaining floors are split so no small Mac is overloaded.

Real live example (Qwen2.5-0.5B, 24 floors):

   M4 Max (64 GB) → embedding + floors 0–19   (the heavy end)
   M4     (16 GB) → floors 20–21
   M5     (16 GB) → floors 22–23 + output head
```

```text
common language:   heaviest boxes go to the strongest mover
technical name:    memory-weighted stage assignment; the embedding table
                   is placed on the highest-capacity rank
```

---

## 4. One training step across 3 Macs

You already know one training step from your Step 6 lesson:
forward → loss → backward → weight update. Forge does the exact same step —
just stretched across machines.

```text
                    ONE TRAINING STEP, THREE MACS

  PHASE A: FORWARD (the sentence climbs)          direction: UP

   Mac 1          "I like tea" → embedding → floors 0..19
                   each floor: attention→residual→norm→MLP
                        │ hidden vectors over network
                        ▼
   Mac 2           floors 20..21 (same work)
                        │ hidden vectors over network
                        ▼
   Mac 3           floors 22..23 → output head → GUESS
                                    "I like tea ___" → guess: "cups"


  PHASE B: GRADE (at the top only)

   Mac 3           compare guess with the correct answer
                   loss = one number for "how wrong"
                   (this is your Step 6 cross-entropy idea)


  PHASE C: BACKWARD (the correction falls)        direction: DOWN

   Mac 3           computes: "how should MY floors change?"
                   also computes: "what error signal do the
                   floors BELOW me need?"
                        │ gradient package over network
                        ▼
   Mac 2           updates ITS floors' adapters;
                   passes the error signal further down
                        │ gradient package over network
                        ▼
   Mac 1           updates ITS floors' adapters. Step done.


  REPEAT.  Loss falls step by step.
  Real run on this fleet: loss 2.9 → 1.9 in 12 steps (1.5B model),
  and 0.38 → 0.15 in 40 steps (0.5B model). Not simulated — measured.
```

The important honesty note (same spirit as your teaching notes): each Mac only
ever knows about ITS OWN floors. Nobody holds the whole model. The coordinator
only carries the introductions — the actual number-traffic flows Mac-to-Mac
through an outbound relay, so nothing ever connects INTO a private machine.

```text
common language:   an assembly line running forward, then a complaints line
                   running backward
technical name:    pipeline-parallel forward/backward pass; activations flow
                   up, gradients flow down
```

---

## 5. LoRA: why small Macs can train big models

Your weight map showed the checkpoint contains ALL weights: WQ, WK, WV, MLP,
norms, embedding, output. Training all of them needs several times the model's
size in memory (weights + gradients + optimizer state). A 16 GB Mac cannot.

Forge's answer — the same trick your notes call "adapters":

```text
             ONE FLOOR, DURING FORGE TRAINING

   ┌───────────────────────────────────────────────┐
   │  WQ  [FROZEN ❄]──┐                            │
   │                  ├─ + tiny adapter A·B  ← LEARNS
   │  WK  [FROZEN ❄]  │   (rank 8, a few thousand  │
   │  WV  [FROZEN ❄]──┘    numbers, not millions)  │
   │  MLP [FROZEN ❄]                               │
   │  norms [FROZEN ❄]                             │
   └───────────────────────────────────────────────┘

   FROZEN  = read every step, never changed
   ADAPTER = the only thing the backward pass updates
```

The math shape, in your notation: instead of updating the big matrix `W`,
Forge learns two skinny matrices `A` (d×8) and `B` (8×d) and uses
`W + A·B` at run time. `A·B` starts near zero, so training starts from the
original model and gently bends it.

In Forge specifically: adapters are attached to each floor's **WQ and WV**
projections, rank 8. That is why the checkpoint shards below are megabytes,
not gigabytes.

```text
common language:   don't rebuild the piano; learn a thin tuning strip
technical name:    LoRA (Low-Rank Adaptation), rank 8 on q_proj/v_proj;
                   base weights frozen, only adapters receive gradients
```

---

## 6. Checkpoints

**What is saved:** each Mac's adapter weights for ITS OWN floors — nothing
else. The frozen base model is never re-saved (it already exists in the model
store), and this is why checkpoints are small.

**Where:** plain files on the coordinator's disk. Not a database. A folder per
run, a subfolder per step.

```text
      EVERY save_every STEPS (e.g. every 8 steps):

   Mac 1 ──► POST stage_2_adapter.safetensors + its SHA-256 ─┐
   Mac 2 ──► POST stage_1_adapter.safetensors + its SHA-256 ─┤
   Mac 3 ──► POST stage_0_adapter.safetensors + its SHA-256 ─┤
                                                             ▼
        coordinator disk:
        checkpoints/cl-6d61dd/step_000040/
        ├── stage_0_adapter.safetensors        (M5's floors)
        ├── stage_1_adapter.safetensors        (M4's floors)
        ├── stage_2_adapter.safetensors        (M4 Max's floors)
        ├── manifest.json    ← which floors each stage covers ("spans")
        │                      + the SHA-256 of every file
        └── COMPLETE         ← written ONLY when every shard has
                               arrived AND its hash matched
```

The all-or-nothing rule (this is the part worth remembering):

```text
   2 shards arrived, 1 missing   →  NO COMPLETE marker
                                    this checkpoint DOES NOT EXIST
                                    for recovery purposes

   Why: the three shards describe DIFFERENT floors. A building
   restored from two-thirds of its floors is not a building.
   Half-saved state must never look usable.
```

```text
common language:   a group photo counts only if everyone is in it
technical name:    per-rank adapter shards + hash verification + an atomic
                   COMPLETE marker; partial checkpoint sets are unrecoverable
                   by construction
```

---

## 7. Failover: a Mac closes its lid

```text
   step 47: M4 stops heartbeating (lid closed)
        │
        ▼
   coordinator waits ~40 s (dead) + a grace window (maybe it's
   just slow) — then marks the run FAILED and tells the
   SURVIVING Macs to stop their now-orphaned processes
        │
        ▼
   find the newest checkpoint folder WITH a COMPLETE marker
   (say step_000040)
        │
        ▼
   pick a spare approved Mac with enough memory for the dead
   Mac's floors — survivors KEEP their own floors and their
   own shards
        │
        ▼
   everyone loads their stage adapters from step 40 and the
   run continues as a new run id. Steps 41–47 are redone.
   That's the whole cost: a few minutes of compute.
```

Note the difference from a database: nothing was "replicated." There is one
copy of each floor's adapters in flight; safety comes from the periodic
all-or-nothing snapshot, not from live copies. (This is the checkpoint/restart
philosophy — cheap and right for batch training, where redoing a few steps is
acceptable.)

```text
common language:   reload the last good save-game
technical name:    heartbeat-based failure detection → resume from the
                   newest COMPLETE checkpoint on a re-placed rank;
                   rank count and stage spans preserved
```

---

## 8. Fuse: welding the pieces back into one model

After training, each Mac holds trained adapters for its own floors — and each
Mac numbered its floors LOCALLY (its first floor is "layer 0" from its own
point of view). Fuse fixes that and produces one file.

```text
   stage_2 (M4 Max): "my layers 0..19"   → really floors  0..19  (+0)
   stage_1 (M4):     "my layers 0..1"    → really floors 20..21  (+20)
   stage_0 (M5):     "my layers 0..1"    → really floors 22..23  (+22)

        │  renumber: add each stage's starting floor
        ▼
   ONE combined adapter file covering floors 0..23
        │
        ▼
   merge into the frozen base model  (W ← W + A·B, per floor)
        │
        ▼
   ONE standalone model file (~241 MB for the 0.5B model)
   — runs anywhere, internet off, yours to keep
```

```text
common language:   three notebooks merged into one book, page numbers fixed
technical name:    remap local layer indices to global by span offset;
                   concatenate adapter shards; mlx_lm fuse into base weights
```

---

## 9. Inference in Forge

Serving is deliberately simpler than training. For models that fit on one Mac,
Forge does NOT split for serving — it picks one capable Mac and runs the model
resident there:

```text
   your app / curl / Xcode ──► https://…/v1/chat/completions
                                        │  (coordinator proxies —
                                        │   one stable URL forever)
                                        ▼
                              SERVE-LEADER MAC
                              model loaded once, stays warm
                              speaks the standard OpenAI protocol
```

Inside that Mac, decode works exactly as in your foundations doc — this is the
same loop, unchanged:

```text
   prompt → PREFILL (read all input tokens, build K/V racks
             on every floor)
        │
        ▼
   DECODE loop:
     old K/V + current position → next-token probabilities
        → pick token → compute its K/V → append to the racks
        → repeat
```

If the serve-leader Mac dies, the coordinator re-homes the model onto a spare
and the URL never changes; if no spare exists it honestly reports DEGRADED
rather than pretending.

```text
common language:   one warm kitchen with a fixed front door
technical name:    resident serve-leader + coordinator /v1 proxy;
                   leader failover with honest degraded state
```

---

## 10. Prefill, KV cache, and the Memory Bus

You learned: **prefill** = reading the prompt and filling the K/V racks;
**decode** = generating. And you learned prefill is the expensive part for
long prompts. Forge's Memory Bus is exactly one idea:

> If many requests share the same big context, do that prefill ONCE and put
> the finished K/V racks on a shared shelf.

```text
   MONDAY, 9:00 — first question about the 100-page handbook

   Mac A:  handbook tokens → prefill through all floors
           → K/V racks for floors 1..24        (the slow part)
                     │
                     │  save the racks to a file ("KV blob"),
                     │  SHA-256 it, publish to the shelf
                     ▼
        ┌───────────────────────────────────────────┐
        │ THE SHELF (Memory Bus)                    │
        │ channel: kv.qwen2-5-0-5b….acme-handbook   │
        │ blob: the K/V racks, hash-verified        │
        │ tokens: 105,000  · reused: 0×             │
        └───────────────────────────────────────────┘

   MONDAY, 9:02 — a DIFFERENT Mac gets a handbook question

   Mac B:  fetch the blob from the shelf (LAN)
           → load racks → SKIP the 100-page prefill entirely
           → prefill only the new question (a few tokens)
           → decode the answer
```

Three rules that make this safe and findable:

```text
1. PREFIX-ONLY.  A shared K/V is valid only as the BEGINNING of the
   input. The handbook must sit at position 0; your new question is
   APPENDED after it. (K/V entries remember their positions — you
   can't paste them into the middle.)

   [ shared handbook K/V ][ your new question ][ answer... ]
    \____ from shelf ____/ \_ prefilled now _/

2. CERTIFIED BYTES.  A blob is stored only if its SHA-256 matches
   what the publisher claimed. "A blob that exists is a blob that
   passed." You can never load a corrupted rack.

3. CHANNELS + WILDCARDS.  Every memory has a dot-separated address:
      kv.<model>.<context>        e.g.  kv.qwen…-4bit.acme-handbook
   Subscribe to one, or to a whole shelf:
      '*'  matches exactly one segment
      '>'  matches everything after
      kv.qwen…-4bit.>   = "every saved context for this model"
```

And the honest constraint: K/V racks are model-specific. A cache made by one
base model fits only that base model (fine-tunes of the same base share it —
that is why the model name is in the channel address).

```text
common language:   a library of already-done readings, checked by fingerprint
technical name:    shared prompt-cache (KV) blobs, content-addressed +
                   hash-verified, prefix-position-only reuse, pub/sub
                   subjects with '*' and '>' wildcards; reuse counted as
                   tokens_saved (prefill work skipped)
```

---

## 11. Model Store

Same "never do it twice" idea, one level lower — the model WEIGHTS themselves:

```text
   WITHOUT the store:  every Mac downloads the same 4 GB from
                       the internet. 10 Macs = 40 GB of internet.

   WITH the store:

   internet ──► ONE storage node downloads the model ONCE
                (keyed "hf:<repo-name>" so it's never duplicated)
                        │
                        ▼
              ┌───────────────────┐
              │ STORE NODE (a Pi  │  advertises what it holds
              │ or any disk box)  │  in its heartbeat
              └───────┬───────────┘
                      │  LAN, your own wires
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
      Mac 1         Mac 2         Mac 3
   "need Qwen"   "need Qwen"   "need Qwen"
      ▲ each job assignment carries: "this model is available
        at node_ip:8808 — fetch locally, skip the internet"
```

If no store node has it, the Mac simply falls back to the internet download —
and once one machine has it pinned, the whole fleet can even run air-gapped.

```text
common language:   one library copy instead of everyone buying the book
technical name:    storage plane; pin → snapshot_download once → content key
                   hf:<repo> → LAN serve; job assignments carry model_lan
```

---

## 12. The Flywheel

Everything above trains a model ONCE. The flywheel is the loop that keeps
training it, safely, from real usage.

```text
                      THE LOOP (one full turn)

     1. USE          your team asks the served model real questions
          │          (every request is recorded as a "trace")
          ▼
     2. KEEP         a human marks good answers as correct
          │          → that answer is now frozen ground truth
          ▼
     3. BUILD        approved traces → a dataset, split TWO ways:
          │            train part  (chat format, the model studies it)
          │            held-out part (LOCKED — never shown in training)
          │          the held-out part is hashed → dataset_hash
          ▼
     4. TRAIN        a real split-across-Macs run (sections 3–6)
          │          on the train part → a CANDIDATE model
          ▼
     5. GRADE        candidate answers the HELD-OUT questions
          │          via the serving endpoint; scored by measured
          │          task-success — never a self-reported number
          ▼
     6. GATE         promote ONLY IF the candidate strictly beats
          │          the current model ON THE SAME dataset_hash
          │          (and meets latency/safety floors).
          │          Wins → it serves. Loses → discarded.
          ▼
     back to 1 — now with a better model producing better answers,
     which become better lessons. The loop compounds.
```

Two honesty mechanisms worth noticing:

```text
• LEAKAGE GUARD: the held-out split is by WHOLE conversation and by
  time, and labels are sealed when the dataset is built — so the
  test can't quietly leak into the training data, and an old score
  can't be reused after labels change (the hash won't match).

• ONE-WAY RATCHET: because losers are discarded, the served model
  can never get worse by this process — only better or unchanged.
```

```text
common language:   practise your own work; keep only what provably wins
technical name:    trace → approve → dataset build (temporal, conversation-
                   level split, sealed labels, dataset_hash) → candidate
                   train → held-out eval → gated promotion, generation++
```

---

## 13. Evals: proof, not vibes

The grading step, on its own, because it is the trust story:

```text
   held-out questions (locked, never trained on)
        │
        ▼
   ask the candidate each one, over the real serving endpoint
        │
        ▼
   for each answer, MEASURE:
     • task success   (does the answer match the sealed label?)
     • latency        (real per-request milliseconds)
     • safety         (every answer non-empty, non-error)
        │
        ▼
   score sheet, e.g.:  candidate 67%  vs  current model 60%
                        → candidate may promote
```

The one rule: the system computes the score itself. A model (or a person)
handing in its own score is never accepted. Both models are always compared on
the exact same locked question set — otherwise the comparison is refused.

```text
common language:   an exam with sealed questions and an external grader
technical name:    held-out task-success evaluation, measured server-side,
                   bound to dataset_hash + evaluator version
```

---

## 14. The Router: cheapest model that fits

Serving cost control, in one flow:

```text
   request arrives at the one door (/v1 gateway)
        │
        ▼
   quick difficulty read (keywords + length):
     "tidy this sentence"          → EASY   (tier 1)
     "summarise this contract"     → MEDIUM (tier 2)
     "prove this edge case"        → HARD   (tier 3)
        │
        ▼
   candidates, sorted by cost:
     your small on-box model      tier 1   ~free
     your promoted fine-tune      tier 2   ~free, private
     big cloud model              tier 3   expensive, data leaves
        │
        ▼
   pick the CHEAPEST OF YOUR OWN models whose tier covers the
   difficulty. The cloud model is never chosen — it is shown only
   as the price you avoided (the ~10× savings number).
        │
        ▼
   two quiet rules:
     • only the flywheel-PROMOTED model receives real traffic
       (the gate decides what serves, not whoever started a server)
     • the router's own answers are logged as new traces —
       so simply USING the router feeds the flywheel
       (fallback answers are flagged and never become lessons)
```

```text
common language:   don't send a bicycle question to a rocket scientist
technical name:    heuristic difficulty tiers → cost-sorted candidate pick;
                   promoted-incumbent-only serving; router traffic logged
                   as flywheel traces
```

---

## 15. Common language → technical name

```text
the manager with the clipboard      →  coordinator / control plane
"I'm here" every 5 seconds          →  heartbeat
workers pull their own tasks        →  pull-based dispatch (no inbound conns)
floors shared across Macs           →  pipeline parallelism
the doorway between floors          →  activation hand-off (hidden states)
sentence climbs / correction falls  →  forward pass / backward pass
thin tuning strip on frozen keys    →  LoRA adapters (rank 8, q/v proj)
group photo only if everyone's in   →  all-or-nothing checkpoint (COMPLETE)
reload the last good save-game      →  checkpoint/restart failover
fix page numbers, merge notebooks   →  layer-index remap + adapter fuse
one warm kitchen, fixed front door  →  serve-leader + /v1 proxy
reading the prompt                  →  prefill (builds K/V)
the reading notes                   →  KV cache
shelf of finished readings          →  Memory Bus (shared KV blobs)
notes only fit at the beginning     →  prefix-only KV reuse
fingerprint check on the shelf      →  content-addressed, SHA-256 certified
one library copy of the book        →  model store (hf:<repo>, LAN serve)
practise your work, keep winners    →  flywheel (trace→train→eval→promote)
sealed exam, external grader        →  held-out eval, measured task success
right-sized worker per request      →  cost-tiered routing
```

---

## 16. Quick reference

| Thing | Unit that moves | Where it lives | Fails how? |
|---|---|---|---|
| Fleet | heartbeats (5 s) | agents ↔ coordinator | silent 40 s = gone |
| Training split | hidden vectors (up), gradients (down) | Mac↔Mac relay | any rank dies → run fails → restore |
| LoRA | tiny adapter matrices | on each Mac's floors | — (base is frozen, can't be damaged) |
| Checkpoint | adapter shards + hashes | files on coordinator | no COMPLETE = doesn't exist |
| Failover | last COMPLETE step | spare Mac takes dead floors | redo a few steps, that's all |
| Fuse | renumbered adapters | one ~241 MB file | refuses on missing shard/span |
| Serving | tokens (decode loop) | serve-leader Mac | re-home to spare, or honest DEGRADED |
| Memory Bus | KV blobs | shelf (coordinator/store nodes) | hash mismatch = blob rejected |
| Model store | whole model repos | store node disk, LAN-served | absent → fall back to internet |
| Flywheel | traces → datasets → candidates | coordinator state + files | loser candidates discarded |
| Evals | held-out Q&A + scores | measured server-side | stale hash = comparison refused |
| Router | one request | gateway → your models | fallback answers never train |

---

### Teaching note (same honesty as your other guides)

The floor counts, spans, loss numbers, and file sizes above are from real runs
on the real fleet (Qwen2.5-0.5B: 24 floors split 0–19 / 20–21 / 22–23 across
M4 Max / M4 / M5; Qwen2.5-1.5B: 28 floors, loss 2.9 → 1.9). The toy Q/K/V
arithmetic lives in your other two guides — this one deliberately stays at the
"what moves between machines and why it's safe" level, because that is the
part your transformer guides don't cover and Forge adds.
