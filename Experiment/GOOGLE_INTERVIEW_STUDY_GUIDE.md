# Google Interview Study Guide

## Built from `01_foundations.md` plus your CockroachDB/MOVR and TDA work

This is a preparation guide, not a prediction of exact questions. The target skill is a repeatable engineering loop:

```text
clarify → model → choose the simplest correct design → prove correctness
       → discuss failure/scale/cost → test edge cases → explain trade-offs
```

## Beginner visual companion — four RRK scenarios

Use this section first. It translates each Google Role-Related Knowledge
scenario into the same plain-language style as the `I like tea` foundation
lessons. In the interview, start with the short answer, draw the ASCII flow,
then zoom into the component the interviewer chooses.

```text
CLARIFY → QUANTIFY → DRAW → EXPLAIN COMPONENTS → TEST FAILURE → MEASURE
  who?      scale?       flow       state/ownership     risk?       SLO/cost?
```

### Four-scenario opening table

| Scenario | Plain-language question | Internal flow | Main control | Measure | Deep dive |
|---|---|---|---|---|---|
| Fine-tuning memory | Why did training run out of GPU memory? | forward → loss → gradients → weight update | profile, reduce, re-measure | peak memory, quality, throughput | [GPU memory](#deep-dive-1--fine-tuning-memory-inside-the-gpu) |
| 600 APIs | How can an agent use old APIs safely? | plan → validate → approve → execute → verify | identity, policy, idempotency, audit | tool accuracy, duplicates, unauthorized calls | [API gateway](#deep-dive-2--600-apis-inside-one-governed-tool-call) |
| Enterprise KMS | How can search respect every user’s permissions? | ingest → index → retrieve → ACL filter → cite | deterministic ACL boundary before generation | recall, freshness, latency, leakage | [KMS search](#deep-dive-3--glean-like-kms-inside-ingestion-and-search) |
| SME underwriting | How can an agent help without making an unsafe loan decision? | extract → verify → analyze → policy → human approval | provenance, deterministic rules, human gate | accuracy, fairness, overrides, audit completeness | [Underwriting](#deep-dive-4--sme-underwriting-inside-one-case) |

## Complete Google RRK preparation map

The four scenarios are the case studies. The interviewer may drill into any of
these supporting skills while you explain them:

```text
                         GOOGLE RRK
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
   LLM / ML              SYSTEMS                 PRODUCT
   fundamentals          engineering             judgment
       │                      │                      │
       ├─ Q/K/V              ├─ APIs                ├─ clarify
       ├─ attention          ├─ queues               ├─ estimate
       ├─ training           ├─ databases            ├─ trade-offs
       ├─ fine-tuning       ├─ caching              └─ rollout
       └─ KV cache          ├─ sharding
                            ├─ observability
                            └─ failure recovery
                              │
                              ▼
                         SAFETY / SECURITY
                         IAM, ACLs, PII,
                         prompt injection,
                         human approval, audit
```

### Preparation checklist

| Area | What you should be able to explain | Scenario connection |
|---|---|---|
| LLM fundamentals | Tokenizer, embeddings, Q/K/V, attention, MLP, logits, KV cache | All four |
| ML systems | Fine-tuning memory, LoRA/QLoRA, quantization, evaluation, cost | Fine-tuning |
| Agentic systems | Planning, tool choice, state, retries, verification, approval | APIs and underwriting |
| System design | APIs, queues, storage, caching, sharding, SLOs | All four |
| Distributed systems | Quorum, replication, idempotency, backpressure, recovery | APIs and KMS |
| Coding | LRU, graphs, DP, parsing, top-K, concurrency | Coding and system components |
| Security | IAM, tenant isolation, ACLs, PII, prompt injection, audit | APIs, KMS, underwriting |
| Product/consulting | Clarify ambiguity, estimate scale, prioritize, explain trade-offs | All four |
| Communication | 30-second answer, 3-minute drawing, deep drill-down | Every question |

### The answer sequence to practise aloud

```text
CLARIFY → QUANTIFY → DRAW → NAME OWNERSHIP → TEST FAILURE
    → ADD SECURITY/HUMAN CONTROL → MEASURE AND ROLL OUT
```

```text
CLARIFY   who uses it, success, risk
QUANTIFY  users, QPS, data, latency, cost, accuracy
DRAW      input → processing → state → decision → output
OWNERSHIP model, runtime, gateway, database, human approver
FAILURE   timeout, duplicate, stale data, bad model, denied access
MEASURE   quality, latency, availability, cost, auditability
```

### Scenario-to-skill map

```text
FINE-TUNING MEMORY
  model weights → gradients → optimizer → GPU memory
  ML fundamentals, profiling, trade-offs, evaluation

600 APIs
  user → agent → tool contract → policy → API → verify
  agents, APIs, IAM, idempotency, retries, audit

GLEAN-LIKE KMS
  sources → connectors → indexes → ACL filter → cited answer
  search, ingestion, distributed systems, security, freshness

SME UNDERWRITING
  documents → evidence → verification → rules → human decision
  workflows, risk, provenance, fairness, human-in-loop
```

```text
30 seconds → business goal + architecture + main risk
3 minutes  → ASCII request path + data stores + ownership
10 minutes → algorithms + failure + security + metrics
deep drill → input, state, algorithm, output, failure mode
```

### Scenario 1 — Fine-tuning memory

Common-language question:

> “Why does training run out of GPU memory, and how can we make it fit?”

Use the LLM foundation analogy:

```text
INFERENCE: the model reads “I like tea” and makes temporary K/V notes.
TRAINING:  the model reads examples, checks the answer, and changes weights.
```

Training GPU memory is not only the model weights:

```text
                 TRAINING GPU MEMORY
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  MODEL WEIGHTS       ACTIVATIONS       TRAINING STATE
  learned recipe      saved layer       gradients
  WQ/WK/WV            values for         Adam moments
  MLP weights         backpropagation    master weights
                         │
                         ▼
                 PEAK MUST FIT GPU
```

```text
“I like tea” during inference       training the model
────────────────────────────       ────────────────────────────
token IDs → embeddings              token IDs → embeddings
24 layers use fixed weights         layers make a prediction
create temporary K/V                compare with correct token
generate answer                     loss → gradients → update weights
```

30-second answer:

> “I separate persistent model state, activations, and temporary buffers. Full
> mixed-precision Adam can require roughly 12–16 bytes per trainable parameter
> before activations, depending on the implementation. I measure peak memory,
> then choose among smaller micro-batches with accumulation, activation
> checkpointing, LoRA/QLoRA, lower precision, sharding, or offload. I compare
> memory against quality, throughput, convergence, and training time.”

Decision tree:

```text
Does the full model fit?
        │
   ┌────┴────┐
  YES        NO
   │          │
profile   reduce micro-batch / checkpoint activations
quality        │
               ▼
        still does not fit?
               │
          ┌────┴────┐
         NO        YES
          │          │
       train     LoRA/QLoRA or shard/offload
```

### Scenario 2 — Make 600 APIs agent-ready

Common-language question:

> “How do we let an agent use 600 old APIs without giving it 600 unsafe
> buttons?”

```text
600 LEGACY APIs
      │
      ▼
inventory + classify risk
      │
      ▼
small task-oriented tool contracts
      │
      ▼
agent chooses a tool
      │
      ▼
identity + policy + schema validation
      │
      ├── low risk → execute
      └── high risk → human approval
                     │
                     ▼
              adapter calls API
                     │
                     ▼
              verify + audit receipt
```

Think of it like the tokenizer lesson:

```text
raw legacy API → normalized tool ID → validated arguments → safe execution
```

30-second answer:

> “I would inventory and risk-classify the 600 endpoints, expose only
> task-oriented versioned tools, and put deterministic identity, policy,
> schema, idempotency, timeout, retry, and audit controls in front of the
> systems of record. I would launch read-only tools first, evaluate tool and
> argument accuracy, then canary side-effecting actions with approval and
> rollback.”

Every side-effecting call follows:

```text
PLAN → VALIDATE → APPROVE → EXECUTE → VERIFY → AUDIT
```

### Scenario 3 — Glean-like enterprise knowledge system

Common-language question:

> “How do we search company knowledge and never show a user a document they
> are not allowed to see?”

```text
Drive / Gmail / Slack / Jira / Git / Confluence
                     │
                     ▼
             connectors + change events
                     │
                     ▼
        raw store → parse → normalize → chunk
                     │
          ┌──────────┼──────────┬──────────┐
          ▼          ▼          ▼          ▼
       BM25       vectors     graph      metadata
          └──────────┼──────────┴──────────┘
                     ▼
user query → authenticate → retrieve candidates
                     │
                     ▼
              enforce user ACLs
                     │
                     ▼
              rerank → cited answer
```

The security invariant is:

```text
candidate document ACL ∩ current user permissions = allowed?
        │                                  │
       NO                                 YES
        │                                  │
 discard before model                  eligible to rank/ground
```

30-second answer:

> “I separate ingestion and query planes. Connectors preserve versions,
> deletions, provenance, and ACLs. I build lexical, vector, metadata, and
> optionally graph indexes. At query time I authenticate the individual user,
> retrieve candidates, enforce permissions before content reaches the model,
> rerank, and generate a cited answer. I measure freshness, relevance,
> latency, faithfulness, and zero unauthorized leakage.”

### Scenario 4 — SME underwriting agent

Common-language question:

> “How can an agent help a Relationship Manager underwrite an SME while a
> human remains accountable?”

```text
documents + bank data + tax data + registry + bureau
                         │
                         ▼
                 durable case workflow
                         │
       ┌─────────┬───────┼────────┬─────────┐
       ▼         ▼       ▼        ▼         ▼
      OCR     extract  verify   cashflow  fraud/policy
       │         │       │        │         │
       └─────────┴───────┴────────┴─────────┘
                         ▼
              evidence + confidence + source
                         │
                         ▼
              deterministic policy checks
                         │
                         ▼
              RM / credit officer approval
                         │
                         ▼
              decision + reason + audit trail
```

Case state machine:

```text
RECEIVED → EXTRACTING → VERIFYING → ANALYZING
    ▲          │             │           │
    └──── request-more-evidence ────────┘
                              │
                              ▼
                    READY_FOR_APPROVAL
                         │       │
                         ▼       ▼
                    APPROVED  DECLINED/ESCALATED
```

30-second answer:

> “I would build an evidence-first durable workflow, not an autonomous loan
> approver. The system extracts facts with confidence and provenance, verifies
> them against authoritative sources, runs deterministic KYC/AML and credit
> rules, identifies contradictions, and pauses for risk-based human approval.
> Every document, model version, policy version, decision, and override is
> auditable.”

```text
LLM suggests and explains.
Deterministic rules verify.
Human approves high-impact decisions.
Audit records what happened and why.
```

### Four-scenario comparison

| Scenario | Main danger | Core control | What to measure |
|---|---|---|---|
| Fine-tuning memory | OOM or quality loss | profile, reduce, re-measure | peak memory, quality, throughput |
| 600 APIs | unsafe side effects | validate, approve, verify | tool accuracy, duplicates, unauthorized calls |
| Enterprise KMS | permission leakage | ACL enforcement before generation | recall, freshness, latency, leakage |
| Underwriting | wrong/un-auditable decision | evidence, rules, human approval | extraction, fairness, overrides, audit completeness |

## Deep visual dives — how each system works internally

These are the drill-down sections. Start with the left side of each diagram in
an interview and zoom into one box only when asked.

### Deep dive 1 — Fine-tuning memory, inside the GPU

#### What happens for one training example?

```text
training example: “I like tea”
correct next token: “tea”
             │
             ▼
       tokenizer → token IDs
             │
             ▼
       embeddings + model weights
             │
             ▼
       forward pass through layers
       Q/K/V → attention → MLP
             │
             ▼
       logits for every vocabulary token
             │
             ▼
       softmax probability: tea = 33%
             │
             ▼
       loss compares 33% with target 100%
             │
             ▼
       backpropagation calculates gradients
             │
             ▼
       optimizer updates selected weights
```

#### Where does memory go?

```text
┌─────────────────────────────────────────────────────────────┐
│ GPU MEMORY                                                  │
├─────────────────────────────────────────────────────────────┤
│ MODEL PARAMETERS                                             │
│ WQ/WK/WV, MLP, norms, embeddings, output head                │
├─────────────────────────────────────────────────────────────┤
│ GRADIENTS                                                     │
│ one correction value for trainable parameters                │
├─────────────────────────────────────────────────────────────┤
│ OPTIMIZER STATE                                               │
│ Adam m/v and sometimes FP32 master weights                   │
├─────────────────────────────────────────────────────────────┤
│ ACTIVATIONS                                                   │
│ hidden vectors saved so backward pass can calculate gradients │
├─────────────────────────────────────────────────────────────┤
│ TEMPORARY WORKSPACE                                           │
│ attention kernels, communication, allocator overhead          │
└─────────────────────────────────────────────────────────────┘
```

#### Why sequence length matters

```text
short prompt:  [I like tea]
long prompt:   [many thousands of tokens]
                         │
                         ▼
more hidden vectors saved for backpropagation
                         │
                         ▼
more activation memory and attention workspace
```

#### The memory-reduction choices

```text
FULL FINE-TUNING
all model weights receive gradients
        │ does not fit?
        ▼
MICRO-BATCH / CHECKPOINTING
less activation memory, more recomputation
        │ still does not fit?
        ▼
LoRA / QLoRA
freeze base weights; train small adapter matrices
        │ still does not fit?
        ▼
SHARD / OFFLOAD
split state across GPUs or move some state to CPU/storage
```

Common-language mapping:

```text
full fine-tuning = rewrite the whole recipe
LoRA             = attach a small correction card to the recipe
checkpointing    = throw away notes and recalculate them later
sharding         = keep different pages on different desks
```

The key interview distinction is that inference usually needs weights plus
temporary K/V state, while training adds gradients, optimizer state, and saved
activations.

### Deep dive 2 — 600 APIs, inside one governed tool call

#### The model does not call a legacy API directly

```text
user: “Refund my last order”
             │
             ▼
       agent planner
       selects refund_order tool
             │
             ▼
       tool contract/schema
       order_id, amount, currency
             │
             ▼
       identity context
       who is acting for which tenant?
             │
             ▼
       policy engine
       is this user allowed? amount allowed?
             │
       ┌─────┴─────┐
       ▼           ▼
    low risk     high risk
       │           │
    execute     human approval
       │           │
       └─────┬─────┘
             ▼
       API adapter
       translates tool call to legacy request
             │
             ▼
       system of record
             │
             ▼
       verify receipt + audit event
```

#### What is inside the gateway?

```text
request ID + tenant + user identity
             │
             ▼
schema validation ── bad input → reject safely
             │
             ▼
authorization/policy ── denied → audit + stop
             │
             ▼
idempotency key ── duplicate → return prior result
             │
             ▼
timeout + retry + circuit breaker
             │
             ▼
legacy API adapter
             │
             ▼
response validation + business invariant
```

#### Why plan, execute, and verify are separate

```text
PLAN       “I will refund order 123 for $20.”
VALIDATE   order exists; amount matches; user is allowed
APPROVE    human approval if policy requires it
EXECUTE    send exactly one idempotent request
VERIFY     receipt says refund succeeded; balance changed correctly
AUDIT      store who, what, why, when, request and response IDs
```

If the network times out after the legacy system processed the refund, do not
blindly retry a payment-like action. Use the idempotency key or query the
system of record first.

### Deep dive 3 — Glean-like KMS, inside ingestion and search

#### Ingestion path: source change to searchable evidence

```text
source connector
   │  document/update/delete event
   ▼
durable event queue
   │  retryable, ordered per source where needed
   ▼
raw immutable object store
   │  preserve original bytes and source metadata
   ▼
parser + normalizer
   │  text, title, author, timestamps, links
   ▼
ACL resolver
   │  users, groups, roles, inherited permissions
   ▼
chunker
   │  stable document/version/chunk IDs
   ├──────────────┬──────────────┬──────────────┐
   ▼              ▼              ▼              ▼
 BM25 index    vector index   metadata index   graph edges
```

A delete is data, not an absence of data:

```text
DELETE event → tombstone/version → remove from every index
             → invalidate cached results → audit completion
```

#### Query path: question to authorized answer

```text
user: “What is the tea reimbursement policy?”
             │
             ▼
authenticate user + tenant
             │
             ▼
query understanding
keywords + entities + filters + intent
             │
       ┌─────┴─────┐
       ▼           ▼
 lexical BM25   dense vectors
       └─────┬─────┘
             ▼
        merge candidates
        (rank fusion / rerank)
             │
             ▼
        enforce ACLs
        remove unauthorized chunks
             │
             ▼
        grounded prompt with citations
             │
             ▼
        answer + source links
```

The critical order is:

```text
retrieve candidates → permission filter → rerank/ground → generate
```

Do not rely on the model to ignore unauthorized text after it has already seen
it. The permission boundary belongs in deterministic retrieval infrastructure.

#### Hybrid search in simple language

```text
BM25 asks:   “Which documents contain the important words?”
vector asks: “Which documents mean something similar?”
graph asks:  “Which people, systems, and documents are connected?”
metadata:    “Which date, team, type, or source matches?”
```

Combine candidates, apply permissions, then use a reranker and citations.

### Deep dive 4 — SME underwriting, inside one case

#### Durable case workflow

```text
case_id + applicant + consent
             │
             ▼
RECEIVED
             │
             ▼
document collection and virus/type checks
             │
             ▼
EXTRACTING
OCR → fields → confidence → page/line provenance
             │
       low confidence?
             ├──────────────► request more evidence
             ▼
VERIFYING
bank/tax/registry/bureau/KYC sources
             │
       contradiction?
             ├──────────────► human review queue
             ▼
ANALYZING
cash flow + repayment capacity + fraud + policy
             │
             ▼
DETERMINISTIC POLICY CHECKS
             │
             ▼
READY FOR RM / CREDIT APPROVAL
```

#### Evidence-to-decision chain

```text
document fact
   │ “monthly revenue = $50k”
   ▼
source + timestamp + confidence
   │
   ▼
verified fact
   │ matches bank/tax evidence?
   ▼
derived metric
   │ debt service coverage / cash-flow trend
   ▼
policy result
   │ within threshold? exception?
   ▼
recommendation with reasons
   │
   ▼
human decision + audit record
```

The model can read, extract, summarize, and explain. It should not silently
invent a missing number or make an irreversible credit decision by itself.

#### What gets recorded for an audit?

```text
case version
document IDs and hashes
extracted facts + page references
external verification responses
model and prompt version
policy/rule version
recommendation and confidence
human approver, decision, reason, timestamp
```

This lets an investigator replay the path:

```text
“Why was this case approved?”
        │
        ▼
facts → verification → calculation → policy → human decision
```

## 1. Foundation concepts in interview language

The attached foundations note follows one LLM request:

```text
text → tokenizer → token IDs → embeddings
     → transformer layers (Q/K/V attention + MLP)
     → prefill (create attention state)
     → decode (generate one token at a time)
     → answer
```

```text
PERMANENT MODEL WEIGHTS              TEMPORARY K/V STATE
learned during training              created during inference
the model's recipe                   notes for this context
reused by every request              may be reused for a matching prefix
```

Interview answer:

> “Weights are the learned recipe. Every transformer layer creates temporary key/value attention state for the current context. A valid prefix cache can avoid repeating old prefill, but the new question and output still need processing. Locally I can validate and restore a native cache; an API provider owns its private cache.”

### Q, K, and V

```text
hidden state
  ├── × WQ → Query: what am I looking for?
  ├── × WK → Key:    what does each token offer?
  └── × WV → Value:  what information is carried?

Q · K → relevance scores → softmax → weighted V → attention output
```

Q/K/V are numerical arrays, not literal English labels. The analogy explains the operation.

### Prefill versus decode

```text
PREFILL                              DECODE
read input context                   generate output
creates K/V state                    appends new state
often prompt-bound                    often serial/latency-bound
```

If 100,000 old tokens are cached and a new question has 50 tokens, the old prefill may be skipped; the 50 new tokens and the answer still require work.

### Local restore versus API cache

```text
LOCAL MLX                              API MODEL
runtime owns native K/V                provider owns private K/V
manifest/fingerprint validation       provider decides hit/miss
load a local tensor file               client receives usage fields
Process B can continue                 no provider tensor download
```

## 2. The Google interview loop

```text
1. Restate the problem.
2. Ask two or three useful clarifying questions.
3. State assumptions.
4. Start with the smallest correct solution.
5. Name the invariant.
6. Walk through a normal and an edge/failure case.
7. Give time and space complexity.
8. Improve for scale, reliability, latency, or cost.
```

Practice in a plain-text editor: no autocomplete, compiler, or hidden AI. Write pseudocode, then code, then dry-run a tiny example.

## 3. Your existing evidence

### CockroachDB / MOVR

```text
MOVR client / Python driver
          │
          ▼
HAProxy :26256  ← one stable SQL endpoint
          │
          ├── n1 :26257
          ├── n2 :26258
          └── n3 :26259
                 │
                 ▼
       ranges + Raft replicas + SQL
```

One-minute story:

> “I built a three-node CockroachDB cluster and routed MovR traffic through HAProxy. I measured a baseline, added and decommissioned a fourth node, then hard-killed a node to observe recovery. I verified three layers: client SQL success, database node/range health, and HAProxy checks. A three-replica range tolerates one failed replica because two votes are a majority; losing two nodes removes quorum and stops safe writes.”

### TDA / research discipline

```text
hypothesis → equal-state-byte baseline → reference implementation
          → tests + gradcheck → multiple seeds → gate / stop / revise
```

| Competency | CockroachDB/MOVR evidence | TDA/foundations evidence |
|---|---|---|
| Correctness | replication, quorum, SQL | reference code, tests, gradcheck |
| Reliability | failure, drain, recovery | restore validation, fingerprints |
| Performance | QPS, p95/p99 | prefill/decode, memory fairness |
| Observability | Console, HAProxy, CLI | run logs, seeds, confidence intervals |
| Communication | endpoint → ranges → replicas | weights → Q/K/V → cache |

Do not call TDA a proven production replacement. Call it a measured research hypothesis with gates.

## 4. Coding patterns

### LRU cache: hashmap + doubly linked list

```text
head (most recent)                         tail (least recent)
   │                                             │
   ▼                                             ▼
 [A] ⇄ [C] ⇄ [B]  ← map: key → node
```

Invariant: every map entry points to one list node, and every list node is in the map. `get` and `put` are O(1) average; space is O(capacity).

```text
get(key): if absent → MISS; otherwise unlink node and move to head
put(key,value): replace/move existing; insert at head; evict before tail
```

### Dynamic programming / sequence alignment

```text
LCS[i][j] = 1 + LCS[i-1][j-1]       if a[i] == b[j]
            max(LCS[i-1][j],LCS[i][j-1]) otherwise

edit[i][j] = edit[i-1][j-1]         if equal
             1 + min(delete,insert,replace) otherwise
```

Say what `dp[i][j]` means before coding. Optimize to two rows only after correctness is clear.

### Streaming parser / DFA

```text
chunk 1: "ab<"  → state = saw '<'
chunk 2: "tag>c" → continue from saved state
```

Never assume a token is contained in one chunk. Preserve explicit state across boundaries.

### Top-K and bounded workers

```text
events → frequency map → min-heap of size K → top K
producer → bounded queue → workers → aggregator
              └── backpressure when full
```

Discuss ordering, retries, duplicate delivery, cancellation, and worker failure.

## 5. System-design template

```text
users and success metric
→ functional/non-functional requirements
→ API and data model
→ request path and state
→ failure modes and recovery
→ scale, latency, cost
→ observability, rollout, security, privacy
→ trade-offs and next iteration
```

### Example: production context-cache gateway

```text
IDE/client → gateway + auth + request ID
                  │
                  ├─ prefix fingerprint / cache lookup
                  ├─ token budget / rate limit / tenant quota
                  ▼
             model router
              ├─ local inference: prefill → K/V restore → decode
              └─ API inference: provider cache hit/miss → decode
                  │
                  ▼
             response + usage + trace
```

Discuss: safe fingerprint mismatch, full-prefill fallback, streaming, tenant isolation, encryption, retention, cache hit rate, prefill/decode p50/p95/p99, token categories, memory, queue depth, and cost.

## 6. Quorum and resilience

```text
three replicas: n1 + n2 + n3 = 3 votes
quorum: floor(3/2)+1 = 2

one node down:  2 votes → quorum remains → safe writes can continue
two nodes down: 1 vote  → quorum lost    → writes stop safely
```

Three live processes do not mean every range has its leader on the same node. Each range can have a different Raft leader.

```text
cockroach node status → node/process liveness
replication dashboard  → under-replicated/unavailable ranges
SQL via HAProxy        → user-visible path
HAProxy stats          → endpoint health and traffic
range report           → leader/follower, lease, ticking, errors
```

Good wording:

> “I do not infer quorum from a green load balancer alone. I check node status, range health, and an application transaction. The decisive rule is a majority of replicas for the affected range, not simply the number of running processes.”

For demos, distinguish hard kill, graceful drain/decommission, restart, and quorum-loss testing. Confirm PID, port, store, and environment before destructive commands.

## 7. One-week plan

| Day | Focus |
|---|---|
| 1 | Read foundations; rehearse the 90-second LLM explanation and one-minute CockroachDB story. |
| 2 | LRU, sliding window, edit distance/LCS; hand-test edge cases. |
| 3 | Chunk-safe parser; retries, ordering, duplicates, backpressure. |
| 4 | Design the context-cache gateway with invalidation, privacy, metrics, and cost. |
| 5 | One coding mock and one system-design mock aloud. |
| 6 | Rehearse baseline → failure → recovery with Console and HAProxy evidence. |
| 7 | Review invariants, complexity, and trade-offs; rest. |

## 8. Mock questions

- **Weights versus K/V cache?** Permanent learned recipe versus temporary context state.
- **Does prefix caching skip the new question?** No; only unchanged old context may be reused.
- **Build LRU.** Map + doubly linked list, invariant, O(1).
- **Parse arbitrary chunks.** DFA/state object survives boundaries.
- **One database node dies?** Affected ranges retain/elect a leader if a majority remains; verify client, range, and endpoint health.
- **What do you measure?** Availability, errors, p50/p95/p99, prefill/decode, hit rate, tokens, memory, queues, and cost.

## 9. Final checklist

```text
[ ] Explain tokenizer, embeddings, Q/K/V, prefill/decode, cache ownership.
[ ] Code LRU and a DP recurrence without autocomplete.
[ ] Preserve parser state across chunks; state invariants aloud.
[ ] Design a reliable context-cache gateway.
[ ] Explain three-replica quorum and one-node failure.
[ ] Show baseline, failure, and recovery evidence.
[ ] Separate measured facts, assumptions, and hypotheses.
```

> “I make complex systems understandable, measurable, and safe to operate. I validate the simple path first, preserve state explicitly, test failure modes, and use evidence before making claims.”

---

# RRK Preparation: The Four Core Scenarios

This section is the main role-related preparation. RRK means **Role-Related Knowledge**. In every scenario, the interviewer is checking whether you can turn an unclear business request into a safe, measurable production system.

## The RRK answer shape

```text
business problem
      ↓
clarify user, scale, quality, latency, risk, control
      ↓
requirements + assumptions
      ↓
architecture and data flow
      ↓
correctness, security, reliability
      ↓
evaluation, rollout, cost, observability
      ↓
trade-offs and next experiment
```

Use this opening:

> “Before choosing a model or product, I want to clarify the user, the business outcome, the risk of an incorrect action, the latency target, the scale, and where human approval is required. Then I will design the smallest measurable production path.”

## Scenario 1 — Fine-tuning memory

### The question

> “You need to fine-tune a large model. What are the memory considerations, and how would you make it fit?”

### Common-language interpretation

The interviewer is asking: **Why did training run out of GPU memory, and what safe choices reduce memory without silently destroying quality?**

```text
GPU MEMORY
   │
   ├── model weights
   ├── gradients
   ├── optimizer states (Adam moments)
   ├── saved activations for backpropagation
   └── temporary kernels / communication buffers
```

### Clarify first

- Model size and architecture?
- Full fine-tuning, LoRA, QLoRA, or preference tuning?
- Precision: FP32, FP16, or BF16?
- Sequence length, micro-batch, and effective batch size?
- GPU memory, number of GPUs, and training deadline?
- Required quality and acceptable compute-for-memory trade-off?

### Speakable answer

> “I separate memory into persistent states, activations, and temporary runtime memory. Full mixed-precision Adam can require roughly many bytes per trainable parameter because it stores weights, gradients, master weights, and optimizer moments; activations can dominate as sequence length and batch size grow. I would first profile peak memory, then choose the least risky reduction: smaller micro-batches with gradient accumulation, activation checkpointing, BF16, LoRA or QLoRA, and finally sharding or offload. I would compare quality, throughput, convergence, and peak memory—not just whether the job starts.”

### Decision tree

```text
Does full fine-tuning fit?
        │
   yes  ├──► profile quality and throughput
        │
   no   ▼
Can we reduce micro-batch / checkpoint activations?
        │
   yes  ├──► keep full weights; accept more compute
        │
   no   ▼
Is every weight required to change?
        │
   no   ├──► LoRA / QLoRA adapters
        │
   yes  ▼
shard optimizer/model state or offload, then re-profile
```

### Mapping to your work

```text
TDA equal-state-byte rule
        │
        ▼
fair comparison before claiming a memory win
        │
        ▼
reference implementation + gradcheck + seeded runs
```

Say: “My TDA work taught me to define the memory budget and comparison rule before looking at results. I would apply the same discipline to fine-tuning: measure peak allocations and report quality and speed with the memory saving.”

### Likely follow-ups

- Why does Adam use more memory than SGD?
- Does gradient accumulation reduce activation memory?
- What does checkpointing save, and what does it not save?
- BF16 versus FP16?
- When would you reject LoRA because quality requires full adaptation?

## Scenario 2 — Making 600 APIs agent-ready

### The question

> “An enterprise has 600 legacy APIs. How would you make them agent-ready end to end?”

### Common-language interpretation

Do not give an LLM 600 dangerous buttons. Build a **governed tool platform** that describes, authorizes, validates, executes, and audits actions.

```text
legacy APIs
    ↓ inventory + ownership + risk classification
tool contracts / schemas / versions
    ↓
agent planner → policy + identity gateway → execution adapters
                         │
                         ├── approval for risky actions
                         ├── idempotency / limits / audit
                         └── timeout / retry / circuit breaker
                                  ↓
                           API systems of record
```

### Clarify first

- Read-only versus mutating or financial APIs?
- Accurate OpenAPI specifications?
- Identity, tenant, and authorization model?
- Function calling, MCP, SDK, or several interfaces?
- Latency, availability, and throughput targets?
- Which actions require mandatory human approval?
- Existing gateway, service mesh, audit, and monitoring?

### Speakable answer

> “I would not expose 600 raw endpoints directly to a model. I would inventory and classify them, normalize their contracts, and wrap them as task-oriented tools with explicit schemas and versioning. A policy and identity gateway validates every proposed call, applies authorization, rate limits, idempotency, approval rules, and audit logging. Reliable adapters execute with timeouts, bounded retries, circuit breakers, and verification. I would start with read-only low-risk tools, evaluate tool selection and argument correctness, then canary higher-risk actions with rollback.”

### Plan–validate–execute–verify

```text
PLAN       model proposes tool + arguments
  ↓
VALIDATE   schema, identity, policy, amount, preconditions
  ↓
APPROVE    human checkpoint when risk requires it
  ↓
EXECUTE    timeout, retry, idempotency key, circuit breaker
  ↓
VERIFY     read-after-write, invariant, receipt, audit event
```

### Mapping to CockroachDB/MOVR

```text
HAProxy stable endpoint        → controlled execution gateway
MovR SQL request               → tool invocation
node/range health checks       → execution health checks
SQL transaction correctness    → business invariant verification
decommission / failure test   → canary, drain, rollback planning
```

Say: “My MOVR exercise reinforced that the client should use a stable endpoint and that health must be verified below the endpoint. For agent tools, the model proposes an action, but a deterministic gateway owns authorization and execution.”

### Metrics

```text
tool-selection accuracy
argument/field accuracy
unauthorized-call rate       → target zero
duplicate-side-effect rate   → target zero
approval precision and burden
successful business task rate
p50 / p95 / p99 latency
cost per completed task
```

### Likely follow-ups

- Why not expose all 600 schemas in one prompt?
- How do you handle API version changes?
- How do you prevent prompt injection from API responses?
- What if the model chooses the right tool with the wrong amount?
- How do you make retries safe for a payment API?

## Scenario 3 — Glean-like enterprise knowledge system

### The question

> “Design an enterprise knowledge system like Glean, including connectors, ingestion, hybrid search, a knowledge graph, and individual-user permissions.”

### Common-language interpretation

Build a search and answer system that is **fresh, relevant, cited, and never leaks a document a user cannot access**.

```text
sources: Drive / Gmail / Slack / Jira / Confluence / DB / Git
      ↓ connectors: full sync + incremental events + deletes
raw versioned store
      ↓ parse → normalize → deduplicate → chunk → extract entities + ACLs
      ├── lexical index (BM25)
      ├── vector index (semantic similarity)
      ├── metadata index
      └── knowledge graph
                                  
user query → authenticate → retrieve → security trim → rerank
                                  ↓
                         grounded answer + citations
```

### Clarify first

- Which sources, document count, users, tenants, and daily changes?
- Search results only, or generated answers too?
- Freshness and deletion SLA?
- Must source ACLs be preserved exactly?
- User-, group-, object-, or field-level permissions?
- p95 search/answer latency and relevance target?
- Data residency, retention, and audit obligations?

### Speakable answer

> “I split ingestion and query planes. Connectors perform full and incremental synchronization while preserving versions, deletions, and source ACLs. Processing parses, normalizes, deduplicates, chunks, and writes lexical, vector, graph, and metadata indexes. At query time I authenticate the individual user, understand the query, retrieve lexical, semantic, and graph candidates, enforce permissions before untrusted text reaches the model, rerank, and generate a cited answer. I would launch only when connector completeness, retrieval quality, freshness, latency, answer faithfulness, and zero unauthorized-document leakage meet their thresholds.”

### The security invariant

```text
candidate document
        │
        ▼
does user principals intersect document ACL?
        │
   no   ├──► discard before model/reranker trust boundary
        │
   yes  └──► eligible for ranking and grounded generation
```

The model must not grant access. Retrieved text is evidence, not instructions.

### Mapping to your foundations and MOVR work

```text
stable prefix / cache fingerprint → versioned document/query state
K/V ownership boundary            → source ACL ownership boundary
cache miss fallback               → lexical-search fallback if vector service fails
HAProxy + node observability      → connector lag + index health dashboards
range replication                 → durable queues and replicated indexes
```

Say: “The important boundary is ownership. The model can summarize authorized evidence, but it cannot decide permissions. Like a database range health check, search health needs separate freshness, completeness, security, and latency signals.”

### Evaluation pyramid

```text
connector completeness / delete correctness
        ↓
retrieval recall + ranking relevance
        ↓
permission correctness / zero leakage
        ↓
answer faithfulness + citation correctness
        ↓
business task success, latency, cost
```

### Likely follow-ups

- Pre-filter versus post-filter security?
- How do you handle a revoked permission while indexes are stale?
- How do you repair a missed webhook?
- Why hybrid search instead of vectors alone?
- How do you prevent retrieved prompt injection?
- What changes during an embedding-model upgrade?

## Scenario 4 — SME underwriting agent

### The question

> “A relationship manager takes a day to underwrite an SME. Design an agentic system that reduces turnaround time, including human approval and verification.”

### Common-language interpretation

This is not “let an AI approve loans.” It is: **collect evidence faster, check it reliably, explain the recommendation, and keep an authorized human accountable.**

```text
SME / relationship-manager portal
              ↓
consent + documents + application data
              ↓
durable case workflow / state machine
      ┌───────┼────────┬─────────┐
      ▼       ▼        ▼         ▼
  OCR/extract verify  financial  policy retrieval
  confidence registry cash flow  current rules
      └───────┬────────┴─────────┘
              ▼
 deterministic policy + risk analysis
              ↓
 critic: contradictions / missing evidence / confidence
              ↓
 human RM or credit officer approval
              ↓
 audited decision + customer communication
```

### Clarify first

- Country, product, regulation, and risk appetite?
- Recommendation, case preparation, or approval?
- Authoritative systems: registry, bank, tax, bureau, KYC/AML?
- Current cases/day and turnaround target?
- False-approval and false-decline tolerance?
- Who has final authority and which checkpoints are mandatory?
- Explanation, audit retention, PII, and residency requirements?

### Speakable answer

> “I would design an evidence-first workflow, not an autonomous loan approver. A durable orchestrator collects and classifies documents, extracts structured facts with confidence and provenance, verifies them against authoritative systems, and invokes deterministic KYC/AML and credit-policy rules. Specialist components calculate cash flow, repayment capacity, anomalies, and sector risk. A critic checks contradictions and missing evidence. The system produces a recommendation with cited evidence and uncertainty, then pauses for the authorized RM or credit officer at risk-based checkpoints. Every input, model/rule version, decision, approval, and override is auditable.”

### Human-in-the-loop state machine

```text
RECEIVED → EXTRACTING → VERIFYING → ANALYZING
    ↑          │             │           │
    │          └─ low confidence ───────┘
    │                        ↓
    └──── REQUEST_MORE_EVIDENCE
                              ↓
                    READY_FOR_APPROVAL
                              ↓
                 APPROVED / DECLINED / ESCALATED
```

### Mapping to your work

```text
MovR tables + SQL correctness     → authoritative case state
CockroachDB failure recovery       → durable workflow/retry behavior
TDA gates and confidence discipline→ evidence before model claims
LLM K/V ownership                  → provenance and permission boundaries
```

Say: “My database exercise taught me to keep durable state and verify after failures. My research work taught me to separate measured evidence from assumptions. For underwriting, those principles become an auditable case state machine and evidence-backed human approval.”

### Metrics and guardrails

- turnaround time and human review time;
- extraction accuracy and verification match rate;
- missing-evidence detection;
- false-approval and false-decline rates;
- override rate and reason;
- fairness metrics by permitted policy groups;
- audit completeness and explanation quality;
- cost per completed case.

### Likely follow-ups

- What if two documents contradict each other?
- What if a source system is unavailable?
- Which steps can be automated and which must remain human?
- How do you prevent a model from inventing financial facts?
- How do you roll back a bad policy or model version?

## RRK comparison card

| Scenario | Main risk | Core architecture | Your strongest bridge |
|---|---|---|---|
| Fine-tuning memory | OOM or quality loss | profile → reduce memory → re-measure | TDA equal-byte experiments |
| 600 APIs | unsafe side effects | tool contract → policy → execute → verify | HAProxy/SQL control path |
| Enterprise KMS | unauthorized leakage | connectors → indexes → security trim → cited answer | MOVR data + foundations cache boundaries |
| Underwriting | wrong or unauditable decision | evidence workflow → deterministic rules → human approval | CRDB durability + TDA evidence discipline |

## RRK rehearsal method

For each scenario, rehearse four versions:

```text
30 seconds  → executive summary
3 minutes   → architecture whiteboard
10 minutes  → reliability, security, evaluation, cost
deep dive   → one difficult follow-up with a concrete trade-off
```

End every answer with:

> “I would launch this in a low-risk slice, instrument the failure and quality metrics, compare the result with an agreed baseline, and expand autonomy only when the evidence meets the gate.”

---

# RRK Deep-Dive Playbook: Concepts, Architecture, Workflow, and Drill Questions

Use this section when the interviewer keeps asking “why?”, “what happens next?”, or “what fails?”. The simple rule is: explain the business idea first, then the architecture, then the control that makes it safe.

## Deep dive 1 — Fine-tuning memory

### Concept in simple language

Fine-tuning means taking an already-trained model and teaching it a specific behavior. During training, the GPU must hold more than the model itself.

```text
model weights       = the current knowledge
gradients           = how each weight should change
optimizer state     = the trainer's running memory
activations         = intermediate notes needed for backpropagation
temporary buffers   = workspace used by kernels and communication
```

Training memory is therefore not just “number of parameters × bytes”. A useful mental model is:

```text
TOTAL PEAK MEMORY
 = parameters + gradients + optimizer + activations + temporary workspace
```

### Concept architecture

```text
training data
     │
     ▼
tokenizer → batches → model forward pass
                         │
                         ├── hidden activations saved
                         └── loss
                              │
                              ▼
                       backward pass
                              │
             gradients + optimizer update
                              │
                              ▼
                       new checkpoint
```

### End-to-end workflow

```text
1. Define quality target and training task
2. Estimate memory before reserving GPUs
3. Run a tiny representative batch
4. Profile peak memory and throughput
5. Choose the least invasive reduction
6. Train with checkpoint/restart support
7. Evaluate quality, safety, speed, and cost
8. Promote only the version that passes the gate
```

### Options and trade-offs

| Option | What it saves | Cost or risk |
|---|---|---|
| Smaller micro-batch | activation memory | more steps; lower throughput |
| Gradient accumulation | preserves effective batch | slower wall-clock update |
| Activation checkpointing | saved activations | recomputes forward work |
| BF16/FP16 | parameter and activation bytes | numerical stability needs testing |
| LoRA | trainable parameters and optimizer state | adapter may lack full-model capacity |
| QLoRA | further base-weight memory reduction | quantization quality/compatibility risk |
| FSDP/ZeRO | sharded state per GPU | communication and operational complexity |
| Offload | GPU pressure | PCIe/host-memory latency |

### Drill questions and simple answers

**Q: Why can a 7B model fail on a GPU that can load 7B inference?**  
**A:** Inference mostly needs weights and runtime memory. Training also needs gradients, optimizer states, saved activations, and temporary buffers, so peak memory is much larger.

**Q: Why does Adam use more memory than SGD?**  
**A:** Adam keeps two additional running statistics per trainable parameter. Those moments improve optimization but consume memory.

**Q: Does gradient accumulation remove activation memory?**  
**A:** It reduces each micro-batch’s activation peak, but it does not remove memory for the model, gradients, or optimizer. It trades memory for more steps.

**Q: What does checkpointing do?**  
**A:** It stores fewer intermediate activations and recomputes them during backpropagation. It saves activation memory, not parameter or optimizer memory.

**Q: When would you choose LoRA?**  
**A:** When the base model is already capable and the task needs a focused behavior. I would validate quality and failure cases before accepting the smaller trainable state.

**Q: How do you know the memory estimate is real?**  
**A:** I run a representative batch, measure peak allocated and reserved memory, vary sequence length and batch size, and compare the profile with the estimate.

**Q: What is your TDA connection?**  
**A:** TDA taught me to fix the state-byte budget and evaluation gate before claiming an improvement. The same principle prevents a memory win that simply hides a quality loss.

## Deep dive 2 — Making 600 APIs agent-ready

### Concept in simple language

An agent can decide **which** tool to request, but deterministic software must decide whether the action is allowed and how it executes.

```text
LLM judgment: “This looks like the right action.”
Code/policy judgment: “This exact action is authorized and safe.”
```

Never allow the model to bypass identity, authorization, limits, or audit.

### Concept architecture

```text
                         CONTROL PLANE
catalog | ownership | risk tier | schemas | versions | policies
                                  │
                                  ▼
user → agent planner → selected tool + arguments
                         │
                         ▼
                 policy/identity gateway
                  │       │        │
                  │       ├── approval queue for high risk
                  │       ├── idempotency + rate limits
                  │       └── audit event
                  ▼
             execution adapters
                  │
                  ▼
          legacy APIs / systems of record
                  │
                  ▼
          verification + result to user
```

### Tool contract example

```text
tool: create_payment
input: {customer_id, amount, currency, reason, idempotency_key}
preconditions: account active; amount within policy; user authorized
side_effect: one payment at most for the idempotency key
result: payment_id + authoritative status
```

### End-to-end workflow

```text
1. Inventory and classify all APIs
2. Fix ownership, schema, authentication, and version gaps
3. Wrap an endpoint as a narrow business tool
4. Add policy, identity, limits, and approval requirements
5. Execute with timeout, bounded retry, and idempotency
6. Verify the authoritative result
7. Emit audit and metrics
8. Canary low-risk tools before mutating tools
```

### Drill questions and simple answers

**Q: Why not put all 600 APIs in the prompt?**  
**A:** It increases token cost and tool confusion. I expose a small relevant catalog, retrieve schemas by task, and keep authorization outside the model.

**Q: What if the model selects the correct API but the wrong amount?**  
**A:** The gateway revalidates amount, currency, account, and policy. The model’s argument is a proposal, not authority.

**Q: How do retries avoid duplicate payments?**  
**A:** Use an idempotency key stored with the business operation. A retry returns the original result instead of creating a second side effect.

**Q: What if the API times out after accepting the request?**  
**A:** Do not blindly retry. Query the operation by idempotency key or use a durable status workflow, then reconcile the authoritative system.

**Q: How do you handle API version changes?**  
**A:** Version the tool contract and adapter, run contract tests, support a migration window, and remove the old version only after usage is zero.

**Q: How do you test agent safety?**  
**A:** Use golden tasks, malformed arguments, adversarial prompts, unauthorized identities, duplicate delivery, and simulated downstream failures. Target zero unauthorized calls and zero duplicate side effects.

**Q: What is your CockroachDB connection?**  
**A:** HAProxy provides a stable entry point, but health and correctness are checked behind it. Similarly, the agent can propose a tool while a gateway owns policy and execution.

## Deep dive 3 — Glean-like enterprise knowledge system

### Concept in simple language

There are two jobs:

```text
INGESTION: keep knowledge complete, current, normalized, and permissioned
QUERY: find only authorized useful evidence quickly and explain it with citations
```

Search relevance is not enough. A perfectly relevant answer from a secret document is a security failure.

### Concept architecture

```text
                  INGESTION PLANE
sources → connectors → durable queue → raw/versioned store
                                      │
                                      ▼
                         parse/normalize/deduplicate
                                      │
                         chunk + metadata + ACL principals
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                  ▼
                 BM25            vector index        graph/metadata

                  QUERY PLANE
user → auth → query understanding → lexical/vector/graph retrieval
                                      │
                                      ▼
                              security trimming
                                      │
                                      ▼
                              rerank → grounded answer
                                      │
                                      ▼
                            citations + audit + metrics
```

### Connector workflow

```text
first sync → checkpoint cursor → fetch page → normalize → index
incremental event → validate version → update or delete → index
missed event? → reconciliation scan → repair drift
poison document? → quarantine → alert → replay after fix
```

### Query workflow

```text
1. Authenticate individual user and tenant
2. Detect language, intent, entities, and filters
3. Retrieve lexical, vector, and graph candidates
4. Apply ACL/security trim before untrusted text crosses trust boundary
5. Rerank a small authorized set
6. Generate only from retrieved evidence
7. Return citations, freshness, and refusal when evidence is weak
```

### Drill questions and simple answers

**Q: Why hybrid search?**  
**A:** Lexical search is strong for exact names and identifiers; vector search is strong for meaning. Combining them improves coverage. A graph adds relationships such as ownership and project links.

**Q: How do you prevent leakage?**  
**A:** Carry source ACL principals with each document and enforce the user-principal intersection before model/reranker access. The model never grants permission.

**Q: What if permissions change after indexing?**  
**A:** Prefer fresh permission checks or a short bounded staleness policy for sensitive sources. A revoked document must be excluded even if its text remains in an index.

**Q: What if a webhook is missed?**  
**A:** Use checkpoints, replayable events, dead-letter handling, and periodic reconciliation/full scans.

**Q: What is prompt injection in a document?**  
**A:** Retrieved content is untrusted evidence. It cannot override system instructions, grant access, or choose tools. Preserve citations and apply content scanning where appropriate.

**Q: How do you measure launch readiness?**  
**A:** Connector completeness, delete correctness, retrieval recall/ranking, permission correctness, answer faithfulness, citation accuracy, freshness, p95 latency, and zero unauthorized leakage.

**Q: What is your foundations connection?**  
**A:** A cached prefix is reusable computation only when identity and content match. A search index is reusable state only when source version and permissions remain valid.

## Deep dive 4 — SME underwriting agent

### Concept in simple language

The system is an assistant for evidence collection and analysis, not an autonomous credit approver.

```text
model proposes and summarizes
rules verify deterministic policy
authoritative systems verify facts
human owns the regulated decision
```

### Concept architecture

```text
RM portal → consent + application + documents
                    │
                    ▼
             durable case state
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
 document      authoritative    policy/risk
 extraction    verification     engines
      └─────────────┬─────────────┘
                    ▼
          evidence reconciliation / critic
                    │
       missing/conflicting? → request evidence
                    │
                    ▼
       recommendation + citations + uncertainty
                    │
                    ▼
           authorized human approval
                    │
                    ▼
       audit, notification, downstream action
```

### End-to-end case workflow

```text
RECEIVED
  → CONSENT_CHECKED
  → DOCUMENTS_CLASSIFIED
  → FACTS_EXTRACTED_WITH_CONFIDENCE
  → FACTS_VERIFIED
  → CASH_FLOW_AND_RISK_ANALYZED
  → CONTRADICTIONS_RECONCILED
  → READY_FOR_APPROVAL
  → APPROVED / DECLINED / ESCALATED
```

Every transition has an owner, timestamp, input version, output, and retry behavior.

### Drill questions and simple answers

**Q: What if two documents disagree?**  
**A:** Do not average or guess. Identify the conflict, rank authoritative sources, request evidence, and escalate if it affects the decision.

**Q: What if a registry or bureau is unavailable?**  
**A:** Mark verification incomplete, retry through a durable workflow, and block or escalate the decision according to policy. Never silently substitute a model guess.

**Q: Which steps can be autonomous?**  
**A:** Low-risk classification, extraction, duplicate detection, and evidence gathering can be automated with confidence thresholds. Credit approval and policy exceptions remain with authorized humans unless explicitly permitted.

**Q: How do you prevent hallucinated financial facts?**  
**A:** Require every material fact to have source provenance, confidence, and a verification status. The answer generator can only use verified evidence or clearly label uncertainty.

**Q: How do you roll back a bad model or policy?**  
**A:** Version models and rules, keep the case’s exact versions, stop rollout with a feature flag, and re-run affected cases under the previous approved version with audit records.

**Q: What is your CockroachDB connection?**  
**A:** A durable database workflow survives process failure and makes state transitions auditable. My MOVR recovery exercise is a concrete example of verifying data after a failure rather than assuming success.

**Q: What is your TDA connection?**  
**A:** TDA’s measured-gate discipline maps to confidence thresholds, false-approval limits, and evidence before expanding autonomy.

## Universal RRK drill checklist

For any of the four scenarios, answer these in order:

```text
WHO uses it and who is harmed if it is wrong?
WHAT is the smallest useful workflow?
SCALE: requests, users, data, updates?
QUALITY: what is correct enough and what is unacceptable?
LATENCY: interactive, near-real-time, or batch?
RISK: privacy, money, regulation, reputation?
CONTROL: autonomous, supervised, or mandatory approval?
STATE: what is authoritative and how is it versioned?
FAILURE: what happens when model, network, source, or node fails?
MEASUREMENT: which metric decides launch or rollback?
```

If interrupted, do not panic. Say:

> “That is an important failure boundary. I will make it explicit in the design, define the safe fallback, and add a metric or test so we can prove it.”
