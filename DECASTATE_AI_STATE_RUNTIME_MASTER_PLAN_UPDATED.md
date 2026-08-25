# DecaState
## The AI State Runtime
### Keep the state. Change the brain.

**Category:** AI State Runtime / Stateful AI Infrastructure  
**Working startup name:** DecaState  
**Primary thesis:** Models, runtimes, and machines should be replaceable while AI state persists.  
**Core promise:** **Persist. Fork. Resume. Transfer. Switch.**

---

# 1. Executive Summary

Modern AI infrastructure is still largely optimized around **requests**:

```text
Request
   │
   ▼
Model
   │
   ▼
Response
```

But AI workloads are becoming increasingly **stateful**:

```text
coding agents
research agents
enterprise copilots
multi-agent systems
local AI
continuous assistants
autonomous workers
long-running workflows
```

These systems accumulate expensive working state:

```text
conversation
tokens
repository understanding
documents
tool outputs
working memory
agent decisions
KV cache
latent inference state
runtime metadata
checkpoints
branch history
```

Today, much of that state is tied to the process, runtime, model, or machine that created it.

When something changes:

```text
process dies
machine restarts
runtime changes
model changes
agent forks
GPU fails
workload moves local → cloud
```

the system often rebuilds context it has already computed.

**DecaState makes AI state a first-class runtime object.**

```text
                    DECASTATE

                 ACTIVE AI STATE
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
    PERSIST           FORK            TRANSFER
       │               │                │
       ▼               ▼                ▼
     RESUME         BRANCHES          SWITCH
                                        │
                                        ▼
                              MODEL / RUNTIME / MACHINE
```

DecaState is not merely:

```text
an LLM router
a KV-cache manager
a chat-history store
an agent framework
an inference server
```

It is:

> **The runtime layer that preserves and moves accumulated AI state across the lifecycle of an AI workload.**

---

# 2. Category Definition — AI State Runtime

An **AI State Runtime** manages the lifecycle of computational state accumulated during AI inference and agent execution.

It provides:

```text
persistence
checkpointing
resume
forking
copy-on-write
rollback
runtime migration
model migration
failover
state-aware routing
compatibility
provenance
```

The category map:

```text
Docker      → containers
Git         → source history
Kubernetes  → workload orchestration
OpenRouter  → model/provider access
Ollama      → local model execution
vLLM        → high-throughput inference
DecaState   → AI state lifecycle
```

---

# 3. The Core Problem

## AI State Is Still Disposable

Today:

```text
Model A
  │
  ▼
100K-token context
  │
  ▼
expensive internal state
  │
  X
process dies
  │
  ▼
rebuild
```

Or:

```text
Model A
  │
  ▼
100K-token session
  │
  ▼
switch to Model B
  │
  ▼
Model B reprocesses context
```

Or:

```text
Base context
  │
  ├── Agent A rereads everything
  ├── Agent B rereads everything
  ├── Agent C rereads everything
  └── Agent D rereads everything
```

This creates four forms of waste:

```text
COMPUTE
MEMORY
LATENCY
RECOVERY TIME
```

---

# 4. Common-Man Explanation

Imagine an AI has spent two hours understanding your project.

It has:

```text
read the code
read documents
used tools
understood decisions
built working context
```

You should be able to:

```text
save it
wake it tomorrow
fork it into 5 workers
roll it back
move it to another runtime
switch it to another model
```

without forcing it to rebuild everything from zero.

That is DecaState.

---

# 5. One-Line Product Pitch

> **DecaState lets AI workloads keep their state even when the model, runtime, process, or machine changes.**

---

# 6. The Core Object: AI State

DecaState treats this as one durable object:

```text
AI STATE
│
├── identity
├── session metadata
├── conversation
├── token stream
├── model fingerprint
├── runtime fingerprint
├── KV / latent inference state
├── agent working state
├── tool state
├── memory references
├── checkpoints
├── branch history
├── provenance
└── compatibility metadata
```

---

# 7. The State Capsule

Persistent state is packaged as a **State Capsule**.

Example:

```text
project-x.dstate
```

Possible structure:

```text
project-x.dstate/
│
├── manifest.json
├── conversation.jsonl
├── tokens.bin
│
├── model/
│   ├── fingerprint.json
│   └── tokenizer.json
│
├── runtime/
│   ├── runtime.json
│   └── cache_layout.json
│
├── inference/
│   ├── kv.safetensors
│   ├── latent.bin
│   └── position.json
│
├── agent/
│   ├── tool_state.json
│   ├── memory_refs.json
│   └── working_state.json
│
├── checkpoints/
│   ├── cp-001/
│   └── cp-002/
│
├── branches/
│   └── graph.json
│
└── provenance/
    └── history.json
```

---

# 8. Core Operations

The product should feel simple:

```text
RUN
SAVE
WAKE
CHECKPOINT
ROLLBACK
FORK
MOVE
SWITCH
ROUTE
```

CLI concept:

```bash
decastate run qwen3:4b
decastate save project-x
decastate wake project-x
decastate checkpoint before-refactor
decastate rollback before-refactor
decastate fork project-x reviewer
decastate move project-x --runtime llama.cpp
decastate switch project-x --model mistral
decastate route project-x --strategy auto
```

---

# 9. Product Architecture

```text
                         APPLICATIONS
                              │
                              ▼
                    ┌───────────────────┐
                    │   DECASTATE API   │
                    └─────────┬─────────┘
                              ▼
                    ┌───────────────────┐
                    │ STATE MANAGER     │
                    │                   │
                    │ lifecycle         │
                    │ checkpoint        │
                    │ fork              │
                    │ rollback          │
                    │ migration         │
                    └─────────┬─────────┘
                              │
           ┌──────────────────┼───────────────────┐
           ▼                  ▼                   ▼
      STATE STORE        CONTEXT ENGINE      COMPAT ENGINE
           │                  │                   │
       manifests          KV / latent         fingerprints
       DAG                COW pages           bridge graph
       provenance         compression         confidence
           │                  │                   │
           └──────────────────┼───────────────────┘
                              ▼
                     ┌────────────────────┐
                     │ CONTEXT BRIDGE     │
                     │                    │
                     │ reuse              │
                     │ convert            │
                     │ translate          │
                     │ repair             │
                     │ recompute          │
                     └─────────┬──────────┘
                               ▼
                      RUNTIME ADAPTERS
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
             MLX           llama.cpp          vLLM
                                                 │
                                              Ollama
```

---

# 10. Why Routing Is Not the Product

OpenRouter and OmniRoute primarily answer:

> **Where should this request go?**

DecaState answers:

> **How should this accumulated state continue?**

```text
REQUEST ROUTER

request
   │
   ▼
choose model
   │
   ▼
response
```

```text
STATE RUNTIME

existing AI state
       │
       ▼
choose destination
       │
       ▼
decide:
reuse?
convert?
translate?
repair?
recompute?
       │
       ▼
continue workload
```

Routing is therefore one capability inside DecaState.

---

# 11. OpenRouter Relationship

Potentially complementary:

```text
                     OpenRouter
                        │
              chooses best model
                        │
                        ▼
                    DecaState
                        │
          moves/preserves AI state
                        │
                        ▼
                  target model
```

OpenRouter:

```text
best provider/model
```

DecaState:

```text
best continuation path
```

---

# 12. OmniRoute Relationship

OmniRoute may decide:

```text
Qwen → Kimi
```

DecaState can handle:

```text
existing state
    │
    ▼
compatibility
    │
    ├── reuse
    ├── translate
    ├── repair
    └── recompute
    │
    ▼
Kimi state
```

So OmniRoute is a potential routing layer; DecaState is the state-continuity layer.

---

# 13. Ollama, vLLM, llama.cpp, MLX and LMCache Relationship

```text
                         DECASTATE
                             │
                 AI state lifecycle layer
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
       MLX               llama.cpp              vLLM
                                                  │
                                                Ollama
```

Possible cache/storage primitives underneath:

```text
native runtime cache
LMCache
local disk
remote object storage
distributed memory
```

DecaState does not need to replace inference runtimes.

It orchestrates state across them.

---

# 14. Killer Feature #1 — Hibernate / Wake

```text
                  ACTIVE AI WORKLOAD

                   Qwen3 / MLX
                        │
                        ▼
                   80K context
                        │
                        ▼
                    HIBERNATE
                        │
                        ▼
                 project.dstate
                        │
                  process exits
                        │
                        ▼
                       WAKE
                        │
                        ▼
                  restore state
                        │
                        ▼
                     continue
```

Benefit:

```text
lower restart latency
less redundant prefill
better local UX
better recovery
```

---

# 15. Killer Feature #2 — Checkpoint / Rollback

```text
T0────T1────T2────T3────T4
      │           │
      ▼           ▼
     C1          C2
                  │
                  ▼
             bad experiment
                  │
                  ▼
              rollback
                  │
                  ▼
                 C1
```

---

# 16. Killer Feature #3 — Fork

```text
                  BASE AI STATE
                       │
                       ▼
                      FORK
             ┌─────────┼─────────┐
             ▼         ▼         ▼
           Coder    Reviewer   Security
```

---

# 17. Killer Feature #4 — Copy-on-Write

Naive:

```text
100K state → Agent A
100K state → Agent B
100K state → Agent C
```

DecaState:

```text
                   SHARED BASE
                     100K
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
           AΔ         BΔ         CΔ
```

Potential benefits:

```text
less duplicated memory
less duplicated storage
faster fork
higher agent density
```

---

# 18. Killer Feature #5 — Runtime Migration

```text
Qwen3 / MLX
    │
    ▼
State Capsule
    │
    ▼
Runtime Adapter
    │
    ▼
Qwen3 / llama.cpp
    │
    ▼
continue
```

This should be solved before cross-model migration.

---

# 19. Killer Feature #6 — Model Migration

```text
Qwen state
    │
    ▼
Context Bridge
    │
    ├── reuse
    ├── translate
    ├── repair
    └── recompute
    │
    ▼
Mistral state
```

---

# 20. Killer Feature #7 — Auto State Router

Decision function:

```text
BestContinuation =
f(
    task quality,
    model capability,
    runtime cost,
    existing state,
    bridge compatibility,
    migration latency,
    prefill avoided,
    translation confidence,
    hardware,
    privacy
)
```

---

# 21. Killer Feature #8 — Failover

```text
Node A
 │
 ▼
active AI state
 │
 ▼
checkpoint
 │
 X
failure
 │
 ▼
Node B
 │
 ▼
restore
 │
 ▼
continue
```

---

# 22. Killer Feature #9 — Local-to-Cloud

```text
MacBook
  │
  ▼
MLX state
  │
  ▼
DecaState
  │
  ▼
cloud GPU
  │
  ▼
vLLM
```

---

# 23. Killer Feature #10 — Session Context Virtualization

DecaState does not magically increase a model's native context window.

But a future state manager could maintain a logical session larger than the active model window:

```text
              LOGICAL SESSION STATE

Page A
Page B
Page C
Page D
Page E
Page F
    │
    ▼
State Pager
    │
    ├── HOT
    ├── WARM
    └── COLD
```

This is analogous to:

```text
virtual memory for AI state
```

---

# 24. Main Customer Pain

Customers do not care about KV-cache terminology.

They care about:

```text
Why does my agent reread the same repository?
Why does restarting lose expensive working state?
Why can't I branch an agent cheaply?
Why must a new model rebuild the same context?
Why can't my state move local → cloud?
Why does a GPU failure mean reconstructing work?
Why are 10 agents holding 10 copies of the same base?
```

---

# 25. Use Case — Coding Agents

```text
Repository
   │
   ▼
150K shared state
   │
   ├── Coder
   ├── Reviewer
   ├── Security
   └── Test Agent
```

Target architecture:

```text
                    REPO BASE STATE
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           Coder      Reviewer     Security
             │           │           │
            ΔC          ΔR          ΔS
```

---

# 26. Use Case — Multi-Agent Systems

```text
                  SHARED BASE STATE
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
         Planner       Coder       Reviewer
            │            │            │
           ΔP           ΔC           ΔR
```

---

# 27. Use Case — Enterprise Research

```text
200 documents
      │
      ▼
base research state
      │
      ├── economics branch
      ├── technical branch
      ├── legal branch
      └── executive branch
```

---

# 28. Use Case — Customer Support Escalation

```text
cheap model
    │
    ▼
conversation grows
    │
    ▼
complex issue
    │
    ▼
switch stronger model
    │
    ▼
preserve state
```

---

# 29. Use Case — Banking

```text
general service model
        │
        ▼
customer context
        │
        ▼
risk detected
        │
        ▼
specialist model
        │
        ▼
same state continues
```

---

# 30. Use Case — Airlines

```text
FAQ assistant
      │
      ▼
disruption detected
      │
      ▼
operations model
      │
      ▼
same state continues
```

---

# 31. Use Case — Local AI

```text
Mac
 │
 ▼
Qwen + MLX
 │
 ▼
work
 │
 ▼
hibernate
 │
 ▼
reboot
 │
 ▼
wake
```

---

# 32. Use Case — GPU Failover

```text
GPU A
 │
 ▼
checkpoint
 │
 X
failure
 │
 ▼
GPU B
 │
 ▼
resume
```

---

# 33. Use Case — Local-to-Cloud Migration

```text
MLX / Mac
    │
    ▼
DecaState
    │
    ▼
vLLM / GPU
```

---

# 34. Use Case — Model Upgrade

```text
Model v1
  │
  ▼
active state
  │
  ▼
bridge
  │
  ▼
Model v2
```

---

# 35. Main Economic Impact

DecaState can create value across:

```text
COMPUTE ↓
MEMORY ↓
LATENCY ↓
RECOVERY TIME ↓
```

---

# 36. Compute Savings

Example:

```text
10 agents
same 200K context
```

Naive:

```text
10 × 200K
=
2M prefix-token processing events
```

Ideal shared base:

```text
1 × 200K
+
deltas
```

Theoretical redundant shared-prefill reduction:

```text
90%
```

This is workload-specific and must not be marketed as universal bill reduction.

---

# 37. Cost Claim Discipline

Never claim:

> "DecaState saves 90% of every AI bill."

Better:

> **"Avoided X% of redundant prefill in measured shared-context workloads."**

or:

> **"Fork N workers from one computed context."**

or:

> **"Resume long-running state without full re-prefill."**

---

# 38. Memory Savings

```text
Without:

KV1 + KV2 + KV3 + KV4

With:

Shared Base KV + Δ1 + Δ2 + Δ3 + Δ4
```

Potential benefit:

> **More concurrent agent sessions per GPU or per Mac.**

---

# 39. Latency Savings

Benchmark:

```text
Cold Restart TTFT
vs.
DecaState Wake TTFT
```

Product message:

> **Resume state instead of rebuilding state.**

---

# 40. Recovery Savings

```text
crash → reconstruct

vs.

checkpoint → crash → wake
```

---

# 41. State Store

Responsibilities:

```text
persistent capsules
checkpoint DAG
deduplication
content addressing
branch metadata
provenance
```

---

# 42. Context Engine

Responsibilities:

```text
KV
latent state
token stream
COW
compression
paging
hot/warm/cold state
```

---

# 43. Compatibility Engine

Determines:

```text
same model?
same weights?
same tokenizer?
same cache layout?
same runtime?
bridge available?
confidence acceptable?
recompute required?
```

---

# 44. Context Bridge

Strategies:

```text
NATIVE REUSE
FORMAT CONVERSION
LEARNED TRANSLATION
REPAIR
SELECTIVE RECOMPUTE
FULL RE-PREFILL
```

---

# 45. Safe Migration Logic

```text
Source state
    │
    ▼
fingerprint check
    │
    ▼
compatible?
  /   \
YES   NO
 │     │
reuse  bridge available?
        /     \
      YES     NO
       │       │
 confidence    safe re-prefill
   /   |   \
high med low
 │    │    │
translate repair recompute
```

---

# 46. State Fingerprint

Every state capsule should include:

```text
model ID
weights hash
tokenizer hash
architecture
attention type
KV heads
head dimension
RoPE
quantization
runtime
runtime version
cache format
dtype
context position
```

---

# 47. Runtime Adapter Interface

Conceptual:

```python
class RuntimeAdapter:
    load_model()
    capture_state()
    restore_state()
    checkpoint()
    resume()
    fork_state()
    convert_state()
    inspect_state()
```

---

# 48. Runtime Roadmap

```text
Phase 1: MLX
Phase 2: llama.cpp
Phase 3: vLLM
Phase 4: Ollama
Phase 5: SGLang
Phase 6: other runtimes
```

---

# 49. Why MLX First

```text
Apple Silicon
Python-native
local
easy instrumentation
direct cache access
fast prototype cycle
```

---

# 50. Why llama.cpp Second

```text
large local ecosystem
different cache representation
cross-platform
GGUF
excellent cross-runtime test
```

---

# 51. Why vLLM Third

```text
production importance
GPU infrastructure
enterprise relevance
distributed serving
KV connectors
```

---

# 52. Model Roadmap

```text
Qwen3
  ↓
Llama
  ↓
Mistral
  ↓
Gemma
  ↓
Phi
  ↓
Kimi / MLA architectures
```

---

# 53. State Portability Ladder

```text
LEVEL 0
same model / same runtime
       ↓
LEVEL 1
same model / process restart
       ↓
LEVEL 2
same model / different runtime
       ↓
LEVEL 3
same family / different model
       ↓
LEVEL 4
cross-family
       ↓
LEVEL 5
different attention architecture
       ↓
LEVEL 6
portable AI state ABI
```

---

# 54. Cross-Model Research Program

Suggested order:

```text
Qwen → Qwen
   ↓
Qwen → Mistral
   ↓
Qwen → Llama
   ↓
Llama → Mistral
   ↓
Kimi-like MLA target
```

---

# 55. Portable AI State

Do not assume native KV is the universal final representation.

Future abstraction:

```text
                 PORTABLE AI STATE
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
 semantic state    token/span map    position state
        │               │                │
        └───────────────┼────────────────┘
                        ▼
                runtime adapter
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
         GQA           MHA           MLA
```

---

# 56. State DAG

```text
                     S0
                     │
                     ▼
                     S1
                   /    \
                  ▼      ▼
                 S2      S3
                 │      /  \
                 ▼     ▼    ▼
                 S4   S5    S6
```

Each node stores:

```text
parent
base reference
delta
checkpoint
model
runtime
timestamp
provenance
```

---

# 57. Content-Addressable Storage

```text
hash(state chunk)
```

Then:

```text
State A ─┐
State B ─┼──► shared physical chunk
State C ─┘
```

---

# 58. Copy-on-Write Engine

```text
base state
   │
   ├── branch A delta
   ├── branch B delta
   └── branch C delta
```

Only changes consume incremental storage.

---

# 59. DecaState Daemon

Local service:

```text
decastated
```

Architecture:

```text
CLI / SDK / API
      │
      ▼
localhost socket
      │
      ▼
decastated
      │
      ├── state manager
      ├── model processes
      ├── state store
      ├── runtime adapters
      ├── bridge engine
      └── metrics
```

---

# 60. CLI

```bash
decastate run qwen3:4b
decastate status
decastate save
decastate wake
decastate checkpoint
decastate rollback
decastate fork
decastate move
decastate switch
decastate inspect
```

---

# 61. API Surface

```http
POST /v1/states
POST /v1/states/{id}/responses
POST /v1/states/{id}/checkpoints
POST /v1/states/{id}/fork
POST /v1/states/{id}/hibernate
POST /v1/states/{id}/resume
POST /v1/states/{id}/move
POST /v1/states/{id}/switch
```

---

# 62. OpenAI-Compatible Layer

Support:

```text
/v1/chat/completions
/v1/responses
```

with:

```text
state_id
```

Example:

```python
response = client.responses.create(
    model="auto",
    state="project-x",
    input="Perform a security review."
)
```

---

# 63. Auto Model / Runtime

Future:

```text
model="auto"
runtime="auto"
```

DecaState decides:

```text
best model
best runtime
best state reuse
best migration strategy
```

---

# 64. Compatibility Explorer

Website:

```text
Source:
Qwen3-4B / MLX

Target                 Status
-----------------------------------
Qwen3-4B / MLX         Native
Qwen3-4B / llama.cpp   Adapter
Qwen3-4B / vLLM        Adapter
Qwen3-8B / MLX         Bridge
Mistral / MLX          Experimental
Llama / vLLM           Experimental
```

---

# 65. Compatibility Metrics

Each path reports:

```text
quality retained
migration latency
prefill avoided
context length tested
hardware
memory overhead
translator confidence
```

---

# 66. State Bridge Registry

Registry object:

```text
Source:
Qwen3-4B / MLX

Target:
Mistral-7B / vLLM

Bridge:
decastate-qwen-mistral-v1
```

Metrics:

```text
quality
latency
context range
hardware
bridge version
confidence calibration
```

---

# 67. Model Context Compatibility Graph

```text
                  Qwen3-8B
                 /   |    \
               .96  .88   .72
               /     |      \
          Qwen3-4B  Mistral  Llama
              │
             .99
              │
             MLX
```

Edges store:

```text
quality
latency
recompute %
context range
runtime
hardware
```

---

# 68. AutoBridge Compiler

Long-term:

```text
source model
+
target model
+
runtime pair
+
small calibration set
      │
      ▼
AutoBridge Compiler
      │
      ▼
bridge
+
confidence model
+
compatibility report
```

---

# 69. Confidence-Aware Migration

```text
Source state
    │
    ▼
Confidence
    │
    ├── high → translate
    ├── medium → translate + repair
    └── low → recompute
```

---

# 70. Selective Recomputation

Goal:

> **Recompute the minimum target state required to maintain quality.**

```text
Layer 00  translate
Layer 01  translate
Layer 02  repair
Layer 03  recompute
Layer 04  recompute
Layer 05  translate
```

---

# 71. Quality-Constrained Migration

```text
minimize:
recompute cost

subject to:
quality >= required threshold
```

---

# 72. ROI Metric #1 — Prefill Avoidance Ratio

```text
reused eligible context
───────────────────────
total eligible context
```

---

# 73. ROI Metric #2 — Resume Acceleration

```text
Cold TTFT
─────────
Wake TTFT
```

---

# 74. ROI Metric #3 — State Amplification

```text
logical state
─────────────
physical state
```

---

# 75. ROI Metric #4 — Fork Latency

Measure:

```text
time to create N agent branches
```

---

# 76. ROI Metric #5 — Agent Density

Measure:

```text
number of useful concurrent agents
per GB memory
```

---

# 77. ROI Metric #6 — Recovery Time

Measure:

```text
crash → useful next token
```

---

# 78. MVP V0.1

Scope:

```text
Mac
MLX
Qwen
local only
```

Features:

```text
run
capture
save
wake
inspect
```

---

# 79. MVP V0.2

Add:

```text
checkpoint
rollback
fork
state DAG
```

---

# 80. MVP V0.3

Add:

```text
copy-on-write
dedup
benchmarks
CLI polish
```

---

# 81. MVP V0.4

Add:

```text
llama.cpp adapter
same-model MLX ↔ llama.cpp migration
```

---

# 82. MVP V0.5

Add:

```text
Qwen-family model bridge
```

---

# 83. MVP V0.6

Add:

```text
Qwen ↔ Mistral
Qwen ↔ Llama
```

---

# 84. MVP V0.7

Add:

```text
vLLM
cloud state store
```

---

# 85. First Hard Proof

> **Can a long Qwen/MLX inference state survive full process death and resume without full re-prefill?**

---

# 86. Second Hard Proof

> **Can one state fork into multiple branches without duplicating the full base?**

---

# 87. Third Hard Proof

> **Can the exact same model migrate MLX → llama.cpp without rebuilding the full context?**

---

# 88. Fourth Hard Proof

> **Can one Qwen model transfer useful state to another Qwen model?**

---

# 89. Fifth Hard Proof

> **Can Qwen state move to Mistral/Llama with measurable quality retention and less re-prefill?**

---

# 90. Benchmark Suite

Track:

```text
cold TTFT
wake TTFT
prefill avoided
checkpoint latency
restore latency
fork latency
storage overhead
memory overhead
KV fidelity
logit KL
perplexity delta
task accuracy
migration latency
recompute fraction
```

---

# 91. 30-Day Plan

Week 1:

```text
MLX state capture
serialization
restore
process-kill test
```

Week 2:

```text
State Capsule
save
wake
inspect
```

Week 3:

```text
checkpoint
rollback
fork
```

Week 4:

```text
COW
dedup
benchmark
GitHub demo
```

---

# 92. 60-Day Plan

```text
llama.cpp adapter
same-model runtime migration
compatibility engine
state format v0.1
public benchmarks
```

---

# 93. 90-Day Plan

```text
Qwen-family bridge
cross-family experiment
compatibility explorer
bridge registry prototype
first design partner
```

---

# 94. Six-Month Plan

```text
vLLM
cloud state store
distributed failover
Auto State Router
enterprise API
cross-model bridge expansion
```

---

# 95. Homepage

Hero:

# **Keep the state. Change the brain.**

Subheading:

> **DecaState is the AI State Runtime for persistent, forkable, portable AI workloads across models, runtimes, and machines.**

CTA:

```text
Get Started
View Compatibility
GitHub
```

---

# 96. Homepage Demo

```text
$ decastate run qwen3:4b

> Understand this repository.

✓ 86K context built

$ decastate checkpoint repo-ready

✓ checkpoint saved

$ decastate fork security

✓ state forked

$ decastate hibernate

✓ state persisted

# kill process / reboot

$ decastate wake security

✓ resumed
```

Later:

```text
$ decastate switch mistral

✓ compatibility checked
✓ state migrated
```

---

# 97. Taglines

Primary:

> **Keep the state. Change the brain.**

Alternatives:

```text
State that survives the model.
Persistent state for AI.
Your AI state, anywhere.
Fork once. Resume anywhere.
The runtime for stateful AI.
```

---

# 98. Open-Source Strategy

Open source:

```text
State Capsule spec
CLI
local daemon
MLX adapter
llama.cpp adapter
checkpoint
fork
COW
benchmark harness
```

Commercial:

```text
cloud state store
distributed sessions
vLLM clusters
enterprise migration
compatibility intelligence
managed bridges
observability
RBAC
audit
HA
```

---

# 99. Developer Flywheel

```text
useful local runtime
      │
      ▼
developers adopt
      │
      ▼
adapters contributed
      │
      ▼
compatibility grows
      │
      ▼
more models/runtimes supported
      │
      ▼
more developers
```

---

# 100. Marketplace Flywheel

```text
developers
   │
   ▼
usage
   │
   ▼
runtime vendors care
   │
   ▼
model vendors certify
   │
   ▼
bridge ecosystem grows
   │
   ▼
more developers
```

---

# 101. Certification

Possible badges:

```text
DecaState Runtime Certified
DecaState Model Certified
DecaState Bridge Certified
```

---

# 102. Business Model

Local:

```text
free / open source
```

Cloud:

```text
managed state storage
cross-device resume
managed migration
remote checkpoints
```

Enterprise:

```text
distributed state runtime
vLLM integration
RBAC
audit
HA
encryption
policy
support
```

---

# 103. Pricing Units

Potential:

```text
managed active states
GB-month state storage
migration operations
enterprise nodes
team subscription
platform subscription
```

Long-term:

```text
performance/savings-linked pricing
```

only if savings measurement is trusted.

---

# 104. First Paying Customer

Best:

> **Coding-agent startup with large shared repository contexts.**

Why:

```text
obvious duplicate state
high agent count
large context
measurable prefill
measurable latency
```

---

# 105. Second Paying Customer

> **Enterprise agent platform**

Needs:

```text
persistent workflows
recovery
audit
multi-model support
```

---

# 106. Third Paying Customer

> **Inference platform**

Needs:

```text
GPU efficiency
session density
failover
state migration
```

---

# 107. Go-To-Market

Phase 1:

```text
Mac-first
local-first
open-source
developer tool
```

Phase 2:

```text
coding agents
multi-agent frameworks
local AI ecosystem
```

Phase 3:

```text
enterprise agents
inference providers
GPU clouds
```

---

# 108. First 100 Users

Target:

```text
MLX developers
LocalLLaMA community
agent builders
coding-agent engineers
AI infrastructure researchers
```

---

# 109. First 10 Design Partners

Ideal:

```text
coding agent startup
enterprise AI team
local AI platform
multi-agent framework
inference provider
```

---

# 110. Competitor Landscape

Adjacent:

```text
OpenRouter
OmniRoute
Ollama
vLLM
llama.cpp
MLX
LMCache
SGLang
agent frameworks
memory products
```

Key distinction:

```text
model access
vs.
inference serving
vs.
cache infrastructure
vs.
AI state lifecycle
```

---

# 111. Competition Matrix

| Product | Model Routing | KV Reuse | Persistent State | Fork/Rollback | Cross-Runtime | Cross-Model |
|---|---:|---:|---:|---:|---:|---:|
| OpenRouter | Strong | No | No | No | No | Request-level |
| OmniRoute | Strong | Limited | Conversational | No | No | Request-level |
| Ollama | No | Native | Limited | No | No | No |
| vLLM | Serving | Strong | Limited | No | Some | No |
| llama.cpp | No | Strong | Partial | Partial | No | No |
| LMCache | No | Very strong | KV-centric | No | Some | Limited |
| **DecaState** | **State-aware** | Uses/extends | **Core** | **Core** | **Core** | **Strategic** |

---

# 112. Moat

Potential moat:

```text
State Capsule standard
runtime interoperability
copy-on-write engine
compatibility graph
bridge compiler
translation confidence
migration telemetry
certification registry
distributed state store
```

---

# 113. Data Moat

Every migration can produce:

```text
source model
target model
source runtime
target runtime
hardware
context length
quality retained
latency
recompute fraction
failure mode
```

This forms a unique compatibility dataset.

---

# 114. Technical Risks

```text
cache incompatibility
restore bugs
tokenizer mismatch
RoPE mismatch
attention architecture mismatch
large state files
serialization latency
COW complexity
cross-model degradation
runtime version drift
```

---

# 115. Product Risks

```text
native runtimes add checkpointing
users accept text-only resume
cross-model bridge remains unreliable
LMCache expands upward
market values portability less than expected
```

---

# 116. De-Risking Logic

```text
same model / same runtime
        │
        ▼
value?
 /   \
yes   no
 │
 ▼
same model / different runtime
        │
        ▼
value?
 /   \
yes   no
 │
 ▼
cross-model
```

The business should not depend on solving the hardest problem first.

---

# 117. Strategic Insight

DecaState can already be valuable with:

```text
save
wake
checkpoint
rollback
fork
COW
failover
same-model runtime migration
```

Cross-model portability becomes the deep moat.

---

# 118. Research Program

Research question:

> **What minimum transferable state allows an AI workload to continue on a different execution environment without rebuilding the full context?**

Sub-questions:

```text
what state is universal?
what state is model-specific?
what state is runtime-specific?
what can be translated?
what must be recomputed?
how can confidence be predicted?
```

---

# 119. Paper Directions

### Systems

> **DecaState: Persistent and Forkable Inference State for Stateful AI Workloads**

### Cross-Runtime

> **Portable Inference State Across Heterogeneous LLM Runtimes**

### Cross-Model

> **StateBridge: Confidence-Aware Context Transfer Across Language Models**

### Standard

> **A Portable State Interface for Interchangeable AI Runtimes**

---

# 120. North-Star Demo

```text
$ decastate run qwen3:4b

> Read and understand this 90K-token repository.

✓ state built

$ decastate checkpoint repo-ready

✓ checkpoint created

$ decastate fork reviewer

✓ forked from shared base

$ decastate switch mistral

Analyzing compatibility...
reuse:       measured
translate:   measured
recompute:   measured

✓ migrated

$ decastate hibernate

✓ persisted

# reboot

$ decastate wake reviewer

✓ restored
```

---

# 121. Category Story

Today:

```text
requests are portable
models are portable
state is not
```

Future:

```text
model
runtime
machine
provider

can change

while

AI STATE
persists
```

---

# 122. Final Architecture Vision

```text
                           USER / AGENT
                                │
                                ▼
                       ┌─────────────────┐
                       │    DECASTATE    │
                       │ AI State Runtime│
                       └────────┬────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
   STATE LIFECYCLE        STATE STORAGE         STATE CONTINUITY
         │                      │                      │
     save/wake               DAG/COW                bridge
     fork                    dedup                  translate
     rollback                paging                 repair
     failover                provenance             recompute
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                ▼
                         RUNTIME ADAPTERS
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
             MLX            llama.cpp            vLLM
              │                 │                 │
              ▼                 ▼                 ▼
            Qwen              Llama             Mistral
                                                    │
                                                  Kimi
```

---

# 123. Final Product Thesis

AI infrastructure is moving from:

```text
stateless request-response
```

to:

```text
long-running stateful execution
```

Stateful execution requires:

```text
persistence
checkpointing
branching
recovery
portability
migration
routing
```

DecaState exists to provide that missing layer.

---

# 124. Final Positioning

# DecaState

## The AI State Runtime

> **Keep the state. Change the brain.**

**Persist · Fork · Resume · Transfer · Switch**

---

# 125. Current Proven Milestone — Native MLX Save/Wake Works

DecaState has now passed its first real native-state persistence proof for the following tested combination:

```text
Model:    Qwen2.5-0.5B-Instruct-4bit
Runtime:  MLX-LM 0.31.3
Platform: Apple Silicon / macOS
```

The test proved:

```text
PROCESS A

36-token prompt
      │
      ▼
native MLX prefill
      │
      ▼
real KV cache created
      │
      ▼
cache captured
      │
      ▼
cache saved to disk
      │
      ▼
PROCESS A EXITS


PROCESS B

fresh process starts
      │
      ▼
same model loads
      │
      ▼
saved native cache loads
      │
      ▼
generation continues
      │
      ▼
original 36 prompt tokens are NOT fully reprocessed
```

The restored continuation exactly matched the native continuation for the tested setup.

A wrong model fingerprint was also correctly rejected.

Therefore, DecaState can now truthfully claim:

> **Native save/wake inference-state persistence works for the tested Qwen2.5-0.5B-Instruct-4bit + MLX-LM 0.31.3 combination.**

This is a validated implementation result, not only an architectural proposal.

It does **not** yet prove:

```text
all Qwen models
all MLX models
all Ollama models
llama.cpp restore
vLLM restore
cross-runtime state movement
cross-model state movement
fork / copy-on-write
universal state portability
```

---

# 126. Why This Matters

The first DecaState thesis is now experimentally demonstrated:

> **An AI workload can build internal inference state once, persist it, terminate completely, and resume later without fully rebuilding the original prompt state.**

In simple language:

```text
WITHOUT NATIVE STATE RESTORE

AI reads context
      │
      ▼
process stops
      │
      ▼
restart
      │
      ▼
AI reads context again
      │
      ▼
continues


WITH DECASTATE SAVE / WAKE

AI reads context
      │
      ▼
state saved
      │
      ▼
process stops
      │
      ▼
state restored
      │
      ▼
continues
```

This is the substrate for checkpointing, rollback, forking, copy-on-write, runtime migration and model migration.

---

# 127. DecaState vs ChatGPT / Claude / Codex / Claude Code

Existing AI products already provide useful continuity, but they operate at a different layer from DecaState.

The key distinction is:

> **Chat products preserve conversation, memory, files, or workspace context. DecaState preserves the model/runtime's actual computational inference state.**

| System | Mainly preserves | What normally happens on continued work |
|---|---|---|
| ChatGPT browser | conversation, memory, files, workspace context | context is supplied to the model again |
| Claude browser | conversation, project context, files | context is supplied to the model again |
| Codex | repository/workspace/task context and execution history | application/workspace state persists, while inference state is rebuilt as required |
| Claude Code | coding workspace, files, conversation/tool context | runtime builds the inference state needed for the next execution |
| **DecaState** | **native inference/runtime state + lifecycle metadata** | **restore already-computed state where safe and supported** |

Simplified:

```text
CHAT HISTORY / MEMORY

previous conversation
        │
        ▼
saved text / files / memory
        │
        ▼
model receives context
        │
        ▼
model builds runtime state
        │
        ▼
answer
```

DecaState:

```text
NATIVE STATE

model receives context
        │
        ▼
model builds runtime state
        │
        ▼
DecaState saves that state
        │
        ▼
process can disappear
        │
        ▼
DecaState restores state
        │
        ▼
continue
```

Common-man analogy:

| Layer | Analogy |
|---|---|
| Chat history | Save the conversation transcript |
| AI memory | Save selected notes/facts |
| Coding workspace | Save the project folder and work history |
| **DecaState** | **Freeze the running internal state and continue from that state later** |

This is why DecaState should not be positioned as another chat-memory product.

---

# 128. Architectural Difference

Conversation continuity:

```text
TEXT / FILES / MEMORY
         │
         ▼
       MODEL
         │
         ▼
  REBUILD EXECUTION STATE
```

DecaState continuity:

```text
TEXT / FILES / MEMORY
         │
         ▼
       MODEL
         │
         ▼
   EXECUTION STATE
         │
         ▼
      DECASTATE
         │
         ├── SAVE
         ├── WAKE
         ├── CHECKPOINT
         ├── ROLLBACK
         ├── FORK
         ├── MOVE
         └── SWITCH
```

DecaState therefore sits **below application memory and above/between inference runtimes**.

---

# 129. Why Existing Coding Agents Still Matter

DecaState should not replace Codex, Claude Code, OpenCode, Hermes or similar agent interfaces.

Instead:

```text
             EXISTING CODING AGENTS

     Codex   Claude Code   OpenCode   Hermes
       │          │           │         │
       └──────────┴─────┬─────┴─────────┘
                        │
                        ▼
                   DECASTATE
                AI State Runtime
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
         MLX        llama.cpp        vLLM
```

The agent remains the user-facing experience.

DecaState becomes the state-lifecycle layer underneath it.

Product message:

> **Keep the coding agent you already use. Stop rebuilding expensive AI state when you do not need to.**

---

# 130. Next Technical Milestones

Now that native MLX save/wake has passed for one tested combination:

```text
NATIVE SAVE / WAKE
        │
        ▼
LONG-CONTEXT BENCHMARK
        │
        ▼
CHECKPOINT / ROLLBACK
        │
        ▼
FORK CORRECTNESS
        │
        ▼
COPY-ON-WRITE / SHARED BASE
        │
        ▼
SAME MODEL / DIFFERENT RUNTIME
        │
        ▼
SAME FAMILY / DIFFERENT MODEL
        │
        ▼
CROSS-FAMILY STATE BRIDGE
```

The next product-quality proof should report:

```text
cold prefill time
wake time
cold TTFT
wake TTFT
saved-state size
prefill avoided
output fidelity
```

Only measured values should be used in marketing.

---

# 131. Updated Product Story

Public hook:

# **Your AI already did the work. Do not make it do it again.**

Platform thesis:

# **Keep the state. Change everything else.**

Distinction from ordinary AI memory:

> **Memory remembers information. DecaState preserves computation.**

---

# 132. Updated Product Position

```text
APPLICATION MEMORY
conversation / files / preferences
             │
             ▼
          AGENT
             │
             ▼
        DECASTATE
      AI State Runtime
             │
             ▼
      INFERENCE RUNTIME
    MLX / llama.cpp / vLLM
             │
             ▼
           MODEL
```

DecaState occupies a different layer from:

```text
ChatGPT memory
Claude projects
agent memory stores
vector databases
request routers
model gateways
```

Its job is to manage the lifecycle of **already-computed AI execution state**.

---

# 133. Updated Validation Status

```text
DECASTATE STATUS

Concept / architecture
PASS

MLX cache internals understood
PASS

Native in-process state replay
PASS

Native disk persistence
PASS

True process-death restore
PASS

Exact continuation for tested model
PASS

Fingerprint mismatch rejection
PASS

Avoided original 36-token re-prefill
PASS

Long-context benchmark
NEXT

Checkpoint / rollback
NEXT

Fork
NEXT

Copy-on-write
FUTURE

MLX → llama.cpp
RESEARCH

Cross-model
RESEARCH
```

This table should be updated as each new phase passes.

