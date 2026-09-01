# DecaState Context Guard

When Claude Code's context fills up, it **compacts**: older messages are replaced by a
model-written summary. The summary is lossy — exact numbers, tool outputs, and decisions
from the middle of a long session can degrade or vanish, and the raw history is no longer
in the model's window.

Context Guard is the recoverable-checkpoint layer for that moment:

```text
Claude Code approaches compaction
        │
        ▼  PreCompact hook (fires automatically)
DecaState Context Guard
        ├── archives the FULL raw transcript (hashed, local)
        ├── builds a structured checkpoint: goals · files touched · commands · test signals
        ├── indexes 100% of the session as verbatim evidence
        └── writes a paste-ready resume brief
        │
        ▼
Claude compacts as normal (Guard never blocks or delays it)
        │
        ▼  later, when the summary isn't enough:
decastate guard-recall "why did the COW experiment fail"
        → returns the EXACT original bytes, with timestamp + provenance
```

## The design principle that makes it trustworthy

**Guard never summarizes.** No model call, no rewriting, no "essence extraction."
It archives verbatim, indexes verbatim, and returns verbatim. The checkpoint is a *map*
of the session, not a replacement for it — the raw archive is always the source of truth.
Lossy summarization is exactly the problem; a tool that answers it with more
summarization would be selling the disease as the cure.

## Install (30 seconds)

```bash
pip install -e .                       # from the DecaState repo
decastate guard-install                # adds the PreCompact hook to .claude/settings.json
                                       # (merges — never clobbers your settings)
# or --scope user for all your projects
```

That's it. Every future compaction in that project auto-checkpoints first.
Manual checkpoint any time: `decastate guard-checkpoint <transcript.jsonl>`.

## Measured on a real session (the one that built this feature)

Run against this project's own live Claude Code session transcript:

```text
transcript          9,921,565 bytes · 2,272 records
extracted           372 user msgs · 215 assistant msgs · 30 files · 139 commands
evidence indexed    801 verbatim entries
checkpoint time     0.052 s
recall test         retrieved exact file bytes from day 1 of the session —
                    content that predated every subsequent compaction — with
                    timestamp provenance
```

## Honest claims table

| Claim | Status |
|---|---|
| Archives the full raw session before compaction | ✅ working, hashed, local-only |
| Returns exact original evidence on demand | ✅ working (verbatim + provenance) |
| Never blocks or slows compaction (exit 0 always) | ✅ by construction |
| Never summarizes or rewrites your history | ✅ by construction — no model calls |
| Reduces context/tokens vs default compaction | ⏳ **unproven** — experiment below |
| Improves post-compaction task quality | ⏳ **unproven** — experiment below |
| Prevents compaction / touches Anthropic's KV cache | ❌ impossible, not claimed |
| Measures subscription dollar savings | ❌ not possible externally, not claimed |

## The experiment (pre-registered — we publish results either way)

Question: does checkpoint + exact recall beat default compaction for long coding sessions?

Protocol:
1. Same repository, same commit, same model, same multi-phase task (long enough to
   force ≥1 compaction). API key + `ANTHROPIC_BASE_URL` through the DecaState gateway
   so token/cost accounting is provider-reported.
2. **Arm A:** default auto-compaction. **Arm B:** Guard checkpoint at the compaction
   boundary + resume from the brief + `guard-recall` for evidence instead of relying
   on the summary.
3. ≥3 runs per arm. Measure: tasks completed without re-asking, tests passing,
   wrong-assumption incidents after the boundary, total input/output tokens, total cost.
4. Raw transcripts and numbers get published in `benchmarks/results/` — including if
   Arm A wins.

Until that lands, Guard's claim is recoverability, not savings. Recoverability alone
is already real: your session history stops being disposable.
