# DECASTATE_CODEX_COMPLETE_BUILD_PLAN.md
## DecaState — AI State Runtime
### Codex Engineering Execution Specification
### Keep the state. Change everything else.

---

# 0. Mission

Build **DecaState**, an experimental open-source AI State Runtime.

Target machine:

```text
MacBook Pro
Apple Silicon M4 Max
64 GB unified memory
macOS
Python
MLX / MLX-LM
```

Initial model:

```text
Qwen3-1.7B
```

The first objective is NOT cross-model translation.

The first objective is:

> Build a long Qwen/MLX context once, persist the real inference state, terminate the process completely, restore that state in a new process, and continue without full re-prefill.

---

# 1. Non-Negotiable Rules for Codex

1. Do not fake KV/state persistence.
2. Do not call chat-history replay "state restore".
3. Do not claim prefill avoidance unless instrumentation proves it.
4. Do not begin cross-model translation before same-model restore works.
5. Do not begin MLX→llama.cpp migration before MLX restore works.
6. Never invent benchmark results.
7. Every performance number must be measured locally.
8. Never inject state into an incompatible model/runtime silently.
9. Keep a safe, explicitly labelled re-prefill fallback where appropriate.
10. Do not auto-commit or push.
11. Do not commit model weights, state capsules, GGUFs, safetensors, logs, secrets, or local paths.
12. Correctness and reproducibility beat feature count.
13. If an API/runtime blocks a feature, document the blocker instead of simulating success.

---

# 2. Product Thesis

Current AI infrastructure:

```text
Request
   │
   ▼
Model
   │
   ▼
Response
```

DecaState:

```text
                    AI STATE
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
    PERSIST           FORK          TRANSFER
       │               │               │
       ▼               ▼               ▼
     RESUME         ROLLBACK         SWITCH
```

DecaState makes accumulated AI state a first-class runtime object.

It is not primarily:

```text
LLM router
API proxy
chat-history DB
vector-memory DB
agent framework
inference server
KV-cache server
```

It is:

> The lifecycle and portability layer for AI execution state.

---

# 3. First Hard Proof

```text
PROCESS A

Long prompt
   │
   ▼
Qwen3 / MLX
   │
   ▼
PREFILL
   │
   ▼
native inference state
   │
   ▼
DecaState SAVE
   │
   ▼
project.dstate
   │
   X
process exits


PROCESS B

project.dstate
   │
   ▼
DecaState WAKE
   │
   ▼
Qwen3 / MLX
   │
   ▼
continue generation
   │
   ▼
NO FULL ORIGINAL PREFILL
```

V0.1 succeeds only if that is real.

---

# 4. V0.1 Acceptance Criteria

All must pass:

```text
[ ] Qwen3-1.7B loads in MLX
[ ] deterministic prompt/context can be prefetched
[ ] real MLX inference state is captured
[ ] state is serialized
[ ] first Python process exits
[ ] second Python process loads model
[ ] state is restored
[ ] next token(s) can be generated
[ ] instrumentation proves original prompt was not fully prefetched again
[ ] native vs restored next-token behavior is compared
[ ] save latency measured
[ ] wake latency measured
[ ] cold-prefill time measured
[ ] state size measured
[ ] fingerprint mismatch rejected
```

---

# 5. Repository

Create:

```text
decastate/
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── Makefile
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── STATE_CAPSULE_SPEC.md
│   ├── MLX_STATE_NOTES.md
│   ├── BENCHMARKS.md
│   ├── COMPATIBILITY.md
│   ├── SECURITY.md
│   └── ROADMAP.md
│
├── decastate/
│   ├── __init__.py
│   ├── version.py
│   ├── cli/
│   │   ├── main.py
│   │   ├── doctor.py
│   │   ├── run_cmd.py
│   │   ├── save_cmd.py
│   │   ├── wake_cmd.py
│   │   ├── inspect_cmd.py
│   │   ├── checkpoint_cmd.py
│   │   ├── rollback_cmd.py
│   │   └── fork_cmd.py
│   ├── state/
│   │   ├── capsule.py
│   │   ├── manifest.py
│   │   ├── fingerprint.py
│   │   ├── validation.py
│   │   ├── lifecycle.py
│   │   └── errors.py
│   ├── runtime/
│   │   ├── base.py
│   │   ├── mlx_runtime.py
│   │   └── registry.py
│   ├── storage/
│   │   ├── local.py
│   │   ├── serializer.py
│   │   ├── layout.py
│   │   └── content_address.py
│   ├── checkpoint/
│   │   ├── manager.py
│   │   ├── dag.py
│   │   └── rollback.py
│   ├── fork/
│   │   ├── manager.py
│   │   └── copy_on_write.py
│   ├── metrics/
│   │   ├── timing.py
│   │   ├── fidelity.py
│   │   ├── counters.py
│   │   └── report.py
│   └── utils/
│       ├── hashing.py
│       ├── paths.py
│       └── logging.py
│
├── experiments/
│   ├── 00_environment_check.py
│   ├── 01_native_mlx_state_replay.py
│   ├── 02_process_death_restore.py
│   ├── 03_long_context_resume.py
│   ├── 04_checkpoint_rollback.py
│   └── 05_fork_baseline.py
│
├── benchmarks/
│   ├── bench_resume.py
│   ├── bench_checkpoint.py
│   ├── bench_fork.py
│   └── results/.gitkeep
│
├── tests/
│   ├── unit/
│   └── integration/
│
└── scripts/
    ├── setup_macos.sh
    ├── run_tests.sh
    ├── run_benchmarks.sh
    └── clean_local_state.sh
```

Do not push anywhere automatically.

---

# 6. Dependencies

Use the Python version actually compatible with current MLX/MLX-LM on the machine.

Likely dependencies:

```text
mlx
mlx-lm
safetensors
typer
pydantic
rich
pytest
pytest-cov
numpy
psutil
```

Inspect versions before pinning.

Do not add heavyweight libraries without need.

---

# 7. Local State Directory

Default:

```text
~/.decastate/
```

Structure:

```text
~/.decastate/
├── states/
├── checkpoints/
├── objects/
├── benchmarks/
├── logs/
└── config.json
```

Allow override:

```text
DECASTATE_HOME
```

Never store large runtime state inside the source repo by default.

---

# 8. `decastate doctor`

Implement first.

It should detect and print:

```text
macOS version
Apple chip
memory if detectable
Python version
MLX version
MLX-LM version
disk free space
DecaState home
model cache status
```

Never hard-code machine facts.

Unknown must be printed as `unknown`.

---

# 9. State Capsule V0.1

Use a durable state object, e.g.:

```text
project-x.dstate/
├── manifest.json
├── conversation.jsonl
├── tokens.bin
├── runtime/
├── model/
├── inference/
└── provenance/
```

Minimum manifest:

```json
{
  "format": "decastate",
  "format_version": "0.1",
  "state_id": "...",
  "created_at": "...",
  "model": {
    "id": "...",
    "weights_fingerprint": "...",
    "tokenizer_fingerprint": "...",
    "architecture": "..."
  },
  "runtime": {
    "name": "mlx",
    "version": "..."
  },
  "context": {
    "token_count": 0,
    "position": 0
  },
  "inference": {
    "state_type": "...",
    "dtype": "...",
    "files": []
  }
}
```

Only store fields that can be determined reliably.

---

# 10. Fingerprinting

Fingerprint enough to prevent unsafe restore:

```text
model identifier
model configuration
tokenizer identity
architecture
quantization when relevant
runtime
runtime version
cache structure metadata
```

Do not hash terabytes of weights if deterministic metadata/config hashing is sufficient for V0.1.

Restore must reject incompatible fingerprints.

---

# 11. Runtime Interface

Create an abstract adapter:

```python
class RuntimeAdapter:
    def runtime_info(self): ...
    def load_model(self, model_id): ...
    def model_fingerprint(self): ...
    def prefill(self, text): ...
    def capture_state(self): ...
    def serialize_state(self, state, path): ...
    def deserialize_state(self, path): ...
    def restore_state(self, state): ...
    def generate_next(self, ...): ...
```

V0.1:

```text
MLXRuntimeAdapter
```

Future:

```text
LlamaCppRuntimeAdapter
VLLMRuntimeAdapter
OllamaRuntimeAdapter
```

Keep MLX internals isolated.

---

# 12. Inspect MLX-LM Before Assuming

Before implementing state persistence, inspect current installed/current MLX-LM source.

Document:

```text
Qwen3 model implementation
cache classes
cache tensor layout
cache offset / token position
prompt-cache helpers
serialization helpers
what must be persisted for exact continuation
```

Write:

```text
docs/MLX_STATE_NOTES.md
```

Reference exact classes/functions/source paths.

---

# 13. Experiment 00 — Environment

`experiments/00_environment_check.py`

Pass conditions:

```text
model loads
tokenizer loads
simple generation succeeds
versions recorded
timings recorded
```

Store machine-readable result.

---

# 14. Experiment 01 — Native State Replay

Before disk persistence, prove state control inside one process.

```text
Prompt
  │
  ▼
Qwen
  │
  ▼
native state
  │
  ├──── continue normally ───► result A
  │
  └──── clone/reload state ──► result B
```

Compare:

```text
first-token logits if accessible
top-1 token
top-k overlap
deterministic continuation
```

Acceptance:

> State replay is numerically or behaviorally consistent within documented tolerance.

Do not use only "the text looks similar".

---

# 15. Experiment 02 — True Process-Death Restore

Process A:

```text
load model
prefill
capture state
serialize state
save reference
exit
```

Process B:

```text
load model
deserialize
restore
generate continuation
measure
```

A supervisor/test must invoke two separate Python processes.

Do not fake restart within one interpreter.

---

# 16. Experiment 03 — Long Context

Benchmark:

```text
1K
4K
8K
16K
```

Increase further only if safe.

For each measure:

```text
cold prefill
cold TTFT
save time
state size
wake time
wake TTFT
fidelity
```

Output JSON + CSV + readable table.

---

# 17. Prefill Avoidance Metric

Do not claim "token savings".

Track:

```text
eligible_prefill_tokens
reprocessed_prefill_tokens
avoided_prefill_tokens
prefill_avoidance_ratio
```

Formula:

```text
avoidance =
avoided_prefill_tokens /
eligible_prefill_tokens
```

Instrument if possible.

Timing alone is not proof.

---

# 18. Resume Speedup

Measure:

```text
cold_resume_time / state_wake_time
```

Always report both raw times and ratio.

---

# 19. Fidelity Metrics

At minimum:

```text
top-1 next-token agreement
top-k overlap
logit cosine similarity if available
KL divergence if practical
deterministic-generation agreement
```

---

# 20. Phase Gate 1

Do NOT continue until:

```text
native replay PASS
process-death restore PASS
fingerprint mismatch rejection PASS
cold-vs-wake benchmark reproducible
fidelity acceptable
```

If any fail:

```text
stop
diagnose
document
fix
```

---

# 21. Phase 2 — Checkpoint / Rollback

Commands:

```bash
decastate checkpoint project-x repo-understood
decastate rollback project-x repo-understood
```

Rollback must restore actual runtime state where supported.

Do not merely truncate messages.

Maintain checkpoint metadata:

```text
checkpoint ID
parent
timestamp
description
state object references
```

---

# 22. State DAG

Use a DAG-friendly internal representation:

```text
                  S0
                  │
                  ▼
                  S1
                /                   ▼      ▼
              S2      S3
                      │
                      ▼
                      S4
```

State objects should be immutable where possible.

---

# 23. Phase 3 — Fork

Command:

```bash
decastate fork project-x reviewer
```

First implementation can physically copy state.

Correctness first.

Acceptance:

```text
parent survives
child starts from same state
branches evolve independently
different prompts create correct divergence
```

---

# 24. Copy-on-Write Research

After correct fork, investigate:

```text
immutable common prefix
content-addressable state chunks
hardlinks/reflinks
runtime-native shared prefix
cache chunk references
append-only deltas
```

Target:

```text
                 BASE STATE
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
        ΔA          ΔB          ΔC
```

Measure:

```text
logical bytes
physical bytes
fork latency
RAM
```

Never claim COW unless actual physical sharing is measured.

---

# 25. Phase Gate 2

Require:

```text
checkpoint PASS
rollback PASS
fork PASS
branch independence PASS
physical/logical storage measurement available
```

---

# 26. Phase 4 — Same Model, Different Runtime

Only after Phase Gates 1 and 2.

Target:

```text
Qwen3 / MLX
     │
     ▼
DecaState representation
     │
     ▼
Qwen3 / llama.cpp
```

Research first.

Document llama.cpp:

```text
KV representation
slot/session persistence
tokenizer
RoPE
position state
cache precision
available save/restore API
```

Write:

```text
docs/LLAMACPP_STATE_NOTES.md
```

If public APIs are insufficient, document exact blocker.

Do NOT silently use prompt replay and call it migration.

---

# 27. Phase 5 — Same-Family Model Translation

After same-model portability is understood.

Start with a small Qwen pair justified by actual geometry.

Research package:

```text
decastate/bridge/
├── base.py
├── capture.py
├── ridge.py
├── translate.py
├── confidence.py
└── evaluate.py
```

Start with:

```text
per-layer
per-head
K and V separately
ridge / linear baseline
```

Measure:

```text
KV reconstruction
attention behavior
first-token logits
perplexity
generation quality
translation latency
native target prefill latency
```

---

# 28. Phase 6 — Cross-Family

Suggested:

```text
Qwen → Mistral
Qwen → Llama
Llama → Mistral
```

Never claim universal portability.

Build a compatibility graph from measured evidence.

---

# 29. Confidence-Aware Migration

Long-term decision:

```text
Source state
    │
    ▼
Compatibility
    │
    ├── native → REUSE
    ├── format-compatible → CONVERT
    ├── high confidence → TRANSLATE
    ├── medium → TRANSLATE + REPAIR
    ├── low → SELECTIVE RECOMPUTE
    └── unsafe → FULL RE-PREFILL
```

Correctness wins over avoiding prefill.

---

# 30. Portable AI State — Research Goal

Do not assume raw KV is universal.

Future:

```text
                 PORTABLE AI STATE
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
 semantic state     token spans     position state
        │               │               │
        └───────────────┼───────────────┘
                        ▼
                  runtime adapter
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
         GQA           MHA           MLA
```

This is not V0.1.

---

# 31. CLI V0.1

Implement fully:

```bash
decastate doctor
decastate run
decastate save
decastate wake
decastate inspect
decastate bench resume
```

Later:

```bash
decastate checkpoint
decastate rollback
decastate fork
decastate move
decastate switch
```

Do not expose commands as stable before they work.

---

# 32. `decastate inspect`

Example:

```text
State ID            ...
Model               ...
Runtime             MLX
Context tokens      ...
Created             ...
State size          ...
Checkpoints         ...
Branches            ...
Fingerprint         valid
Restore mode        native
```

Unknown fields must say `unknown`.

---

# 33. Benchmark Command

Implement:

```bash
decastate bench resume   --model <model>   --tokens 1000,4000,8000,16000
```

Later:

```bash
decastate bench fork --branches 2,4,8
```

Output:

```text
table
JSON
CSV
```

---

# 34. Benchmark Metadata

Record:

```text
timestamp
OS
chip
memory
Python
MLX
MLX-LM
model ID
model config hash
quantization
context tokens
decode settings
git commit if available
```

---

# 35. Security / Privacy

State may contain sensitive:

```text
conversation
documents
code
tool output
KV / latent representations
```

Therefore:

```text
local-only by default
no automatic upload
clear data location
safe delete command later
file permission awareness
future encryption documented
```

---

# 36. `.gitignore`

Ignore at least:

```text
.venv/
__pycache__/
.pytest_cache/
.DS_Store
.env
*.dstate
*.safetensors
*.gguf
models/
logs/
benchmark raw state/
```

Do not commit local model/state artifacts.

---

# 37. Tests

Unit:

```text
manifest
fingerprint
capsule
validation
storage
DAG
```

Integration:

```text
MLX native replay
separate-process restore
wrong-model rejection
checkpoint
rollback
fork
```

Heavy model tests should be local/opt-in.

---

# 38. Error Types

Create:

```text
DecaStateError
StateNotFoundError
StateCorruptError
FingerprintMismatchError
RuntimeUnsupportedError
RestoreUnsupportedError
BridgeUnavailableError
UnsafeMigrationError
```

No silent exception swallowing.

---

# 39. Version Plan

Suggested:

```text
0.0.1 native replay
0.1.0 save/wake across process death
0.2.0 checkpoint/rollback
0.3.0 fork/COW
0.4.0 llama.cpp experiment
0.5.0 same-family bridge
0.6.0 cross-family experimental
1.0.0 stable AI State Runtime API
```

---

# 40. 30-Day Execution Plan

Week 1:

```text
doctor
inspect MLX source
Qwen load
native state capture
native replay
fidelity metrics
```

Week 2:

```text
State Capsule
serializer
process-death restore
save/wake CLI
fingerprint guard
resume benchmark
```

Week 3:

```text
checkpoint
rollback
DAG
tests
```

Week 4:

```text
fork
COW experiment
fork benchmark
README demo
```

---

# 41. 60-Day Plan

```text
stabilize local API
investigate llama.cpp
adapter prototype
same-model cross-runtime feasibility
compatibility metadata
public measured compatibility table
```

---

# 42. 90-Day Plan

Only if earlier gates pass:

```text
Qwen pair capture
ridge translator
target cache injection
quality metrics
translation latency
confidence estimator
compatibility explorer
first cross-family experiment
```

---

# 43. Product Metrics

Primary:

```text
Prefill Avoidance Ratio
Wake Speedup
Fork Latency
Logical / Physical State Ratio
Recovery Time
```

Later:

```text
Migration Quality Retention
Translation Latency
Selective Recompute Fraction
```

---

# 44. Claim Rules

Allowed only after measurement:

```text
"X× faster wake on Qwen... at Y-token context on this M4 Max"
"Z% redundant prefill avoided in this benchmark"
"N branches share one measured base state"
```

Not allowed without proof:

```text
"90% cheaper AI"
"works with every model"
"universal state portability"
"zero quality loss"
"instant migration"
```

---

# 45. Viral Product Wedge

Do NOT launch publicly with:

> Cross-model KV translation infrastructure.

Launch with:

# Never make your AI rebuild the same state twice.

Initial visible operations:

```text
SAVE
WAKE
CHECKPOINT
FORK
```

Research complexity stays underneath.

---

# 46. README Hero

After V0.1 really works:

```text
# DecaState

## Keep the state. Change everything else.

Persist, resume, checkpoint and fork live AI inference state.
```

CLI:

```bash
decastate run qwen...
decastate save repo
decastate wake repo
decastate fork repo reviewer
```

Only list supported features.

---

# 47. Viral Demo 1

Show:

```text
1. Build long context
2. Save state
3. Kill process
4. Wake state
5. Continue
6. Show cold-vs-wake benchmark
```

---

# 48. Viral Demo 2

Show:

```text
ONE REPO STATE
      │
      ├── CODER
      ├── REVIEWER
      └── SECURITY
```

with measured fork time and measured physical state sharing.

---

# 49. Future Runtime Matrix

Populate from evidence:

```text
Runtime       Capture   Restore   Fork   Cross-runtime

MLX           measured  measured  measured research
llama.cpp     research  research  research research
vLLM          later     later     later   later
Ollama        later     later     later   later
```

No false green checkmarks.

---

# 50. Future Model Matrix

Populate from evidence:

```text
Family        Native Resume   Same-family Bridge   Cross-family

Qwen          first           research             research
Llama         later           later                research
Mistral       later           later                research
Kimi/MLA      later           N/A                  advanced
```

---

# 51. V0.1 Definition of Done

This exact workflow works on the target Mac:

```bash
decastate doctor

decastate run <qwen-model>   --context-file ./sample.txt   --state project-x

decastate save project-x

# terminate all DecaState/model Python processes

decastate wake project-x

decastate inspect project-x

decastate bench resume --state project-x
```

Evidence shows:

```text
correct fingerprint
real state persisted
new process restored
original context not fully prefetched
continuation valid
benchmark generated
```

---

# 52. V0.2 Definition of Done

```bash
decastate checkpoint project-x repo-understood
decastate fork project-x reviewer
decastate rollback project-x repo-understood
```

All must manipulate actual runtime state, not only text history.

---

# 53. Stop Conditions

Stop and report clearly if:

```text
MLX state cannot be fully serialized
restore materially corrupts logits
prompt replay is unavoidable
public runtime APIs block injection
fork cannot preserve native state
cross-runtime format cannot be mapped
```

Negative results are useful.

Do not disguise them.

---

# 54. Required Documentation

Keep current:

```text
README.md
docs/ARCHITECTURE.md
docs/STATE_CAPSULE_SPEC.md
docs/MLX_STATE_NOTES.md
docs/BENCHMARKS.md
docs/COMPATIBILITY.md
docs/SECURITY.md
docs/ROADMAP.md
```

---

# 55. Codex Working Method

For each milestone:

```text
1. State hypothesis
2. Inspect runtime source/API
3. Build smallest experiment
4. Execute it
5. Record raw result
6. Add automated test
7. Refactor into product module
8. Benchmark
9. Update docs
10. Stop at gate
```

Do not scaffold later phases prematurely.

---

# 56. Codex Status Report

After each work session report:

```text
DECASTATE STATUS

Current phase:
Hypothesis:

Completed:
- ...

Tests:
- X passed
- Y failed

Measured:
- ...

Blockers:
- ...

Files changed:
- ...

Next exact task:
- ...

Claims now supported:
- ...

Claims NOT yet supported:
- ...
```

---

# 57. FIRST CODEX TASK — DO THIS NOW

Build **Phase 0 only**:

```text
1. Create repo skeleton.
2. Implement `decastate doctor`.
3. Inspect current MLX-LM Qwen/cache implementation.
4. Write docs/MLX_STATE_NOTES.md.
5. Load Qwen3-1.7B.
6. Prefill deterministic context.
7. Capture native MLX inference state.
8. Clone/replay it in the same process.
9. Compare next-token logits/tokens.
10. Add automated integration test.
11. Produce status report.
```

DO NOT yet build:

```text
llama.cpp adapter
vLLM
Ollama
HTTP API
cloud
website
cross-model translation
marketplace
AutoBridge
```

---

# 58. Phase Gate Before Persistence

Codex must explicitly answer:

```text
Can current MLX-LM state be captured and replayed correctly?
YES / NO

What exact cache classes/functions were used?

What tensor/state pieces are required?

What fidelity was measured?

What remains unknown?
```

Only if `YES`, proceed to process-death persistence.

---

# 59. Final Product Architecture

```text
                           USER / AGENT
                                │
                                ▼
                       ┌─────────────────┐
                       │    DECASTATE    │
                       │ AI State Runtime│
                       └────────┬────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
 STATE LIFECYCLE          STATE STORAGE           STATE CONTINUITY
       │                        │                        │
 save / wake                DAG / COW                bridge
 checkpoint                 dedup                    convert
 rollback                   paging                   translate
 fork                       provenance               repair
 failover                                             recompute
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                ▼
                         RUNTIME ADAPTERS
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
            MLX             llama.cpp             vLLM
             │                  │                  │
             ▼                  ▼                  ▼
           Qwen               Llama             Mistral
                                                    │
                                                   Kimi
```

---

# 60. Engineering Principle

> **Never rebuild state when it can be safely reused. Never reuse state when correctness cannot be demonstrated.**

---

# 61. Command for Codex

Paste this file into the repository/project context and tell Codex:

> Read `DECASTATE_CODEX_COMPLETE_BUILD_PLAN.md` completely. Build only Phase 0 first. Follow the non-negotiable rules and phase gates exactly. Do not implement future phases until the current gate passes. Run the experiments on this Mac, record real measurements, and finish with the required DECASTATE STATUS report.

