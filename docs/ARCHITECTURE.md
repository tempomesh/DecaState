# Architecture

The implementation is local-first. Runtime-native MLX persistence is proven and shipped (save/wake/checkpoint/rollback/fork — see `make phase1` and `benchmarks/results/`), and a second proven backend drives llama.cpp over llama-server's slot save/restore API (`decastate/backends/llamacpp.py`). An earlier Ollama-backed path with metadata-only capsules remains as a demo. Cross-model bridges remain gated research work. The launch-level overview lives in [../ARCHITECTURE.md](../ARCHITECTURE.md).

Native MLX state is now also stored as immutable checkpoint objects. Checkpoint manifests record model/runtime fingerprints, context position, lineage, provenance, and the serialized MLX-LM prompt-cache object. Rollback loads the native cache directly; it does not replay prompt history.

Fork correctness currently creates independent physical copies of a native cache. Copy-on-write and physical sharing are deliberately not claimed.

Product architecture remains broader than fork storage:

```text
DECASTATE — AI STATE RUNTIME
├── lifecycle: save / wake / checkpoint / rollback
├── sharing: fork / dedup / copy-on-write
└── portability: runtime move / model bridge / state-aware routing
```

## Q/K/V fundamentals (local MLX)

Transformer attention uses three numerical objects:

```text
Q = Query   → what the current token is looking for
K = Key     → labels/signals describing earlier tokens
V = Value   → information carried by earlier tokens
```

For a new token, the model compares its query with earlier keys, then uses the
matching values to predict the next token:

```text
new Q
  │
  ├── compare with previous K
  │
  └── select useful V ──→ next-token prediction

attention = softmax(Q × Kᵀ) × V
```

The runtime normally retains K and V for earlier positions. Q for the current
position is calculated and used immediately; it is not the durable part of the
prompt cache.

The tested Qwen MLX checkpoint contains 24 transformer layers. Every layer has
one Key tensor and one Value tensor:

```text
24 layers × (1 Key + 1 Value) = 48 tensors
```

The serialized cache is a `safetensors` file. In the tested artifact,
`native-cache.safetensors` is about 25 MB and a representative tensor has:

```text
shape = (1, 2, 2047, 64)
        │  │  │     └── 64 values per attention head
        │  │  └──────── 2,047 processed token positions
        │  └──────────── 2 KV heads
        └─────────────── batch size 1
```

The 2,047 value is a sequence-position count, not a word count. A token may
be a word, part of a word, punctuation, or whitespace. The corresponding
metadata is in `manifest.json` as `token_count` and `cache_position`.

## Model weights, K/V creation, and storage boundaries

### Model weights are permanent learned parameters

Model weights are the large numerical files produced by training. They encode
the model's learned ability to process language and code. They are not the
conversation context and they are not the KV cache.

```text
MODEL WEIGHTS
  = permanent learned numbers
  = the model's capability
  = normally unchanged during inference

KV CACHE
  = temporary attention numbers
  = the context already processed in this session
  = grows as new tokens are processed
```

An open-weight model means that its weight files are available to download and
run locally. It does not necessarily mean that the training data, training
recipe, or all surrounding infrastructure is public.

### How weights create Q, K, and V

The model uses its learned projection weights during every forward pass:

```text
user text
   │
   ▼
tokenizer → token IDs → embeddings
                              │
                              ▼
                    transformer attention layer
                       ┌──────┼──────┐
                       ▼      ▼      ▼
                 Q = h × WQ  K = h × WK  V = h × WV
                       │      │      │
                       └──────┼──────┘
                              ▼
                 attention = softmax(Q × Kᵀ) × V
                              │
                              ▼
                         next token
```

`WQ`, `WK`, and `WV` are parts of the permanent model weights. The model
creates numerical Q/K/V arrays; it does not label them with words such as
`"MLX cache"` or `"file location"`. Those labels are teaching analogies. The
actual values are floating-point vectors associated with token positions,
attention heads, and layers.

### Local MLX path

On the tested Apple Silicon setup, MLX loads the model weights and performs
inference using the Mac's Apple GPU/unified memory when available:

```text
YOUR MAC

model weights + tokenizer
          │
          ▼
       MLX runtime
          │
          ▼
   Apple GPU / memory
          │
          ▼
     creates K/V state
          │
          ▼
 DecaState serializes the state
          │
          ▼
.decastate/checkpoints/<state>/<checkpoint>/
  ├── native-cache.safetensors
  └── manifest.json
```

### API model path

With Claude or OpenAI, the model weights and inference hardware remain on the
provider's infrastructure:

```text
YOUR COMPUTER
  user prompt
      │
      ▼
  Claude Code / Codex API client / application
      │
      ▼
  optional DecaState gateway
      │  routing, hashing, cache annotations, usage audit
      │
      ▼  HTTPS over the internet
PROVIDER SERVER
  private model weights
      │
      ▼
  provider GPU/accelerator creates Q/K/V
      │
      ▼
  provider server-side prompt/KV cache
      │
      ▼
  generated response + usage fields
      │
      ▼
YOUR COMPUTER
```

The provider normally returns generated text and usage information. It does
not expose its private model weights, raw GPU memory, or raw provider KV
tensors to DecaState.

### Ownership boundary

```text
DecaState owns locally:
  request routing, hashes, manifests, evidence, local MLX cache files,
  fingerprints, save/restore, and measured reports.

The provider owns remotely:
  model weights, inference hardware, Q/K/V tensors, and server-side cache.

The model owns:
  attention computation, reasoning, and the generated answer.
```

Therefore local and API caching are related ideas but different mechanisms:

```text
LOCAL MLX
  DecaState can save and restore native K/V tensors.

API MODEL
  DecaState can request/measure provider prompt caching,
  but cannot download or restore the provider's private K/V tensors.
```

For a completely transparent educational version, run:

```bash
source .venv/bin/activate
make tiny-demo
```

`experiments/07_tiny_10param_llm.py` is deliberately a toy one-layer model
with exactly 10 parameters. It demonstrates the mechanics and prints the
actual scalar Q/K/V values, attention percentages, prediction, and cache flow.
It is not a quality benchmark or a replacement for Qwen/Claude/OpenAI.

## Baby-step transformer curriculum

We use small lessons before discussing a production-scale LLM:

```text
STEP 1  text → tokenizer → token IDs → embedding vectors       ← current
STEP 2  embeddings → one transformer layer → Q/K/V
STEP 3  Q × Kᵀ → softmax → weighted V (attention)
STEP 4  attention → feed-forward network → layer output
STEP 5  repeat layers → logits → next-token probabilities
STEP 6  loss → backpropagation → weight updates (training)
STEP 7  save K/V → restore K/V → continue without prefill
```

### Prefix and prefill

The prefix is the unchanged beginning of an input. Prefill is the computation
that reads input tokens and creates their K/V attention state.

```text
[stable prefix] + [new question]
       |
       +-- first request: prefill all input -> create K/V
       |
       +-- later request: reuse prefix K/V
                          + prefill only new tokens
                          -> decode the answer
```

```text
WITHOUT VALID STATE
100,000 old tokens + 50 new tokens -> prefill 100,050 tokens

WITH VALID PREFIX STATE
old prefix reused    + 50 new tokens -> prefill 50 new tokens
```

The application/runtime chooses the candidate stable prefix. The model creates
Q/K/V during inference. A local DecaState runtime can validate and restore its
own native K/V state. With an API model, DecaState can preserve and annotate a
stable prefix, but OpenAI or Anthropic makes the final provider-cache hit/miss
decision.

### Local MLX example

The saved local state has two useful parts:

```text
manifest.json
  readable metadata: model, token count, position, fingerprint

native-cache.safetensors
  binary K/V tensor arrays created by the local MLX runtime
```

`<STATE_ID>` is a placeholder. Replace it with a real directory returned by
`find`. For example, one existing state is
`coding-demo-1787535612330`.

Inspect the metadata:

```bash
python -m json.tool .decastate/states/coding-demo-1787535612330/manifest.json
```

Inspect tensor names, shapes, and dtypes:

```bash
.venv/bin/python - <<'PY'
from safetensors import safe_open

path = ".decastate/checkpoints/coding-demo-1787535612330/repo-understood/native-cache.safetensors"
with safe_open(path, framework="numpy") as f:
    for key in f.keys():
        tensor = f.get_tensor(key)
        print(key, tensor.shape, tensor.dtype)
PY
```

```text
manifest + cache file
          |
          v
DecaState validates model, tokenizer, fingerprint,
position, and file integrity
          |
     +----+----+
     |         |
    PASS      FAIL
     |         |
restore      reject restore
native K/V   and prefill again
     |
skip old prefix prefill
     |
continue generation
```

Run Step 1 with:

```bash
source .venv/bin/activate
make step1
```

The lesson intentionally stops before Q/K/V. For `I like tea`, it shows the
token sequence `[<BOS>, I, like, tea]`, IDs `[0, 1, 2, 3]`, and a small
four-number embedding vector for each position. Real LLMs use much larger
vocabularies and vectors, but the operation is the same: the first transformer
layer receives numbers, not raw words.

## What process-death restore means

This is a real two-process test, not merely a pause inside one Python process:

```text
Process A
  load model
  prefill repository prompt
  create K/V state
  save native-cache.safetensors
  exit — its RAM and PID disappear

native-cache.safetensors remains on disk
                 │
                 ▼

Process B
  load model again
  validate model/runtime fingerprint
  load the saved K/V tensors
  continue generation
```

DecaState does not need to guess whether Process A died. The test explicitly
exits Process A, then starts Process B independently. Successful continuation
and exact replay prove that the state survived outside Process A's memory.

This local mechanism is different from an API provider cache:

```text
Local MLX cache       DecaState can save, inspect, fingerprint, and restore.
Anthropic/OpenAI KV   Provider owns it; DecaState sees usage, not tensors.
```
