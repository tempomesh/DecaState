# LLM Foundations Before Step 2

This is the plain-language guide before building the next transformer lesson.
It explains what happens from typing a prompt to getting an answer, and where
local KV restore and API prompt caching save repeated work.

No claim in this document says that the model skips the new question. The old
context may be reused; the new question and the new answer still need to be
processed.

## Toy LLM progress map — read this first

This table is the permanent roadmap for our educational miniature model. The
first twelve steps are implemented as small educational scripts.
The toy model explains the ideas; the real Qwen/MLX experiments are separate.

| Step | What we build or learn | Status | Direct link |
|---|---|---|---|
| 1 | Text → tokens → token IDs → embeddings | Done | [`01_tokens_embeddings.py`](01_tokens_embeddings.py) |
| 2 | Embeddings → Q/K/V projections | Done | [`02_embeddings_qkv.py`](02_embeddings_qkv.py) |
| 3 | Q/K scores → softmax → weighted V attention | Done | [`03_attention.py`](03_attention.py) |
| 4 | Attention → residual → normalization → MLP | Done | [`04_transformer_layer.py`](04_transformer_layer.py) |
| 5 | Hidden vector → logits → next-token probabilities | Done | [`05_logits_next_token.py`](05_logits_next_token.py) |
| 6 | Loss → gradients → weight updates | Done | [`06_training_loss_backprop.py`](06_training_loss_backprop.py) |
| 7 | Train tiny model → freeze weights → inference | Done | [`07_tiny_train_then_infer.py`](07_tiny_train_then_infer.py) |
| 8 | Fine-tuning memory: loss, GPU buckets, and mitigations | Done | [`08_finetuning_memory.py`](08_finetuning_memory.py) |
| 9 | Connect multiple transformer layers into one forward pass | Done | [`09_multi_layer_forward.py`](09_multi_layer_forward.py) |
| 10 | Train the toy Q/K/V and attention weights | Done | [`10_train_qkv_attention.py`](10_train_qkv_attention.py) |
| 11 | Generate several tokens continuously | Done | [`11_tiny_generation_loop.py`](11_tiny_generation_loop.py) |
| 12 | Add, save, and restore a toy KV cache | Done | [`12_toy_kv_cache_save_restore.py`](12_toy_kv_cache_save_restore.py) |
| 13 | Advanced fundamentals: causal mask, MHA/GQA/MQA, MoE, and memory | Done | [`13_advanced_fundamentals.py`](13_advanced_fundamentals.py) |
| 14 | Attention types: self, causal, bidirectional, local, and cross | Done | [`14_attention_types.py`](14_attention_types.py) |
| 15 | MHA, GQA, MQA, and KV-cache memory math | Done | [`15_mha_gqa_mqa.py`](15_mha_gqa_mqa.py) |
| 16 | Dense MLP versus MoE router and experts | Done | [`16_dense_vs_moe.py`](16_dense_vs_moe.py) |
| 17 | Training versus inference memory and optimization | Done | [`17_training_inference_memory.py`](17_training_inference_memory.py) |

Run the completed lessons in order:

```bash
make step1
make step2
make step3
make step4
make step5
make step6
make step7
make step8
make step9
make step10
make step11
make step12
make step13
make step14
make step15
make step16
make step17
```

The key boundary is:

```text
Steps 1–12: our transparent learning model
Real Qwen/MLX: loaded separately by experiments/phase1_native_state.py
DecaState: saves/restores the real model's native inference state
```

### Weight coverage in our toy lessons

| Step | Weight or parameter | What it does in the lesson |
|---|---|---|
| 1 | Embedding table | Converts token IDs into small vectors; hand-written here |
| 2 | `WQ`, `WK`, `WV` | Creates Query, Key, and Value views |
| 3 | No new learned weight | Calculates attention from Q, K, and V |
| 4 | `W_MLP` | Applies the tiny feed-forward transformation |
| 5 | Output weights | Converts the hidden vector into token logits |
| 6 | Output weights | Updates weights using loss and gradients |
| 7 | Output weights | Trains, freezes, and uses them for inference |
| 8 | Training memory buckets | Accounts for weights, gradients, optimizer state, activations, and buffers |
| 9 | Existing layer weights | Runs the same transformer block repeatedly to show depth |
| 10 | `WQ`, `WK`, `WV` | Learns attention projections from a tiny training example |
| 11 | Existing model weights | Uses the trained forward path repeatedly, one generated token at a time |
| 12 | No new model weight | Saves/restores temporary toy K/V state; weights remain separate and fixed |
| 13 | Router scores and memory formulas | Demonstrates attention access rules, K/V sharing, MoE selection, and memory buckets |
| 14 | Causal-mask rules | Shows which tokens can see which other tokens |
| 15 | KV-head layout | Shows why MHA/GQA/MQA use different cache sizes |
| 16 | Router scores | Shows dense MLP versus selected MoE experts |
| 17 | Training bookkeeping | Shows gradients/optimizer state versus inference K/V state |

The toy lessons do **not** yet include every real Qwen parameter. A full model
also has positional/RoPE parameters, attention output projections, MLP
gate/up/down projections, normalization parameters, and these weights repeated
across every transformer layer. The real MLX runtime loads those complete
weights internally.

## One-picture explanation: the model is a bread stack

```text
                 ONE TOKEN JOURNEY

"I" → [token ID 1] → [embedding numbers]
                              │
                              ▼
        ┌──────────────────────────────────┐
        │ SLICE 24                         │
        │ attention + MLP                  │
        │ uses trained weights             │
        │ makes the meaning more complete  │
        └──────────────────────────────────┘
                              ▲
        ┌──────────────────────────────────┐
        │ SLICE 3                          │
        │ attention + MLP                  │
        │ uses trained weights             │
        │ passes improved numbers upward   │
        └──────────────────────────────────┘
                              ▲
        ┌──────────────────────────────────┐
        │ SLICE 2                          │
        │ attention + MLP                  │
        │ uses trained weights             │
        └──────────────────────────────────┘
                              ▲
        ┌──────────────────────────────────┐
        │ SLICE 1                          │
        │ Q/K/V attention + MLP            │
        │ uses WQ/WK/WV and other weights  │
        └──────────────────────────────────┘
                              ▲
             embeddings for BOS, I, like, tea

        ... slices 4 through 23 are between these slices ...

                              │
                              ▼
                 output weights → next token
```

```text
PERMANENT MODEL WEIGHTS                 TEMPORARY K/V CACHE
trained recipe used by every prompt     working notes for this prompt
       │                                        │
       └── each slice uses them                 └── each slice creates K/V
```

---

## 1. The complete path from your computer to an LLM

```text
YOU TYPE
  "I like tea"
      |
      v
YOUR APP / CODING AGENT
  Claude Code, Codex client, MLX app, or DecaState
      |
      v
TOKENIZER
  text -> token pieces -> token IDs
      |
      v
EMBEDDINGS
  token IDs -> vectors of numbers
      |
      v
TRANSFORMER LAYERS
  attention, Q/K/V, feed-forward calculations
      |
      v
NEXT-TOKEN PREDICTION
  the model generates the answer one token at a time
```

---

## 2. Tokenizer

A tokenizer is a text-to-number tool. It is not the language model.

```text
Text:
  I like tea

Tokenizer:
  [BOS, I, like, tea]

Token IDs:
  [0,   1,  2,    3]

Embeddings:
  [vector, vector, vector, vector]
```

`BOS` means **Beginning Of Sequence**. It marks the start of the input.
`UNK` means **Unknown**. It is a fallback used when a tokenizer cannot
represent a text piece. Modern tokenizers often split unusual words into
smaller pieces instead.

Tokenizers are model-specific. Qwen, Claude, and OpenAI may count the same
sentence differently. Tokenization itself does not create a discount. It only
turns text into the model's input units. Provider pricing uses that provider's
token count.

## 3. Transformer as a stack of bread slices

Each transformer layer is like one slice in a stack. The whole model passes the
token vectors through every slice from bottom to top.

```text
                         OUTPUT
                           ▲
                 ┌─────────────────┐
                /  SLICE 24        /│
               / attention + MLP  / │
              └─────────────────┘  │
              │  hidden vectors    │
              └────────────────────┘
                 ┌─────────────────┐
                /  SLICE 3         /│
               / attention + MLP  / │
              └─────────────────┘  │
              │  hidden vectors    │
              └────────────────────┘
                 ┌─────────────────┐
                /  SLICE 2         /│
               / attention + MLP  / │
              └─────────────────┘  │
              │  hidden vectors    │
              └────────────────────┘
                 ┌─────────────────┐
                /  SLICE 1         /│
               / attention + MLP  / │
              └─────────────────┘  │
              │ token vectors     │
              └────────────────────┘
                           ▲
                    input embeddings
```

For the tested Qwen2.5-0.5B model, the stack has 24 transformer layers. In
simple language, the same token information passes through 24 trained workers.

```text
token vectors
     │
     ▼
worker 1 improves the information
     │
     ▼
worker 2 improves it again
     │
     ▼
worker 3 improves it again
     │
    ...
     │
     ▼
worker 24 produces the final understanding
     │
     ▼
choose the next token
```

Each worker is one transformer layer. One slice contains an attention part and
a feed-forward/MLP part:

```text
ONE TRANSFORMER SLICE

input hidden vectors
        │
        ├── multiply by WQ/WK/WV weights
        │       │
        │       └── Q, K, V
        │
        ├── attention calculation
        │
        ├── residual + normalization
        │
        ├── MLP/feed-forward weights
        │
        └── output hidden vectors → next slice
```

Common-language version:

```text
Each layer receives numbers.
It uses its learned weights to ask:

  "Which earlier words matter right now?"
  "What information should I carry forward?"
  "How should I improve this meaning?"

Then it passes improved numbers to the next layer.
```

### Zoom: the token vectors entering the stack

This is a four-number teaching example, not the full Qwen vector size:

| position | token | token ID | embedding |
|---:|---|---:|---|
| 0 | `<BOS>` | 0 | `[0.0, 0.0, 0.0, 1.0]` |
| 1 | `I` | 1 | `[1.0, 0.0, 0.0, 0.1]` |
| 2 | `like` | 2 | `[0.0, 1.0, 0.0, 0.2]` |
| 3 | `tea` | 3 | `[0.0, 0.0, 1.0, 0.3]` |

```text
                 token positions →
              0          1          2          3
          <BOS>         I       like        tea

embedding  [0,0,0,1] [1,0,0,.1] [0,1,0,.2] [0,0,1,.3]
              │          │          │          │
              └──────────┴──────────┴──────────┘
                         │
                         ▼
                 BREAD SLICE 1
                 creates Q/K/V
                         │
                         ▼
                 BREAD SLICE 2
                 creates new Q/K/V
                         │
                        ...
                         │
                         ▼
                 BREAD SLICE 24
                         │
                         ▼
                  next-token scores
```

### Where do the model weights come from?

```text
TRAINING TIME                         USE TIME / INFERENCE
------------                          --------------------
text examples                         load trained weights
     │                                          │
     ▼                                          ▼
calculate prediction                   read token IDs
     │                                          │
     ▼                                          ▼
compare with correct answer            use WQ/WK/WV/MLP weights
     │                                          │
     ▼                                          ▼
backpropagation updates numbers        calculate Q/K/V and attention
     │                                          │
     ▼                                          ▼
save final model checkpoint             generate answer
```

The model checkpoint contains the learned weights. The experiment does not
train Qwen; it loads already-trained weights. The K/V cache is created later,
during inference, for the particular prompt being processed.

```text
model weights = permanent learned recipe
K/V cache     = temporary notes from this conversation
```

### Complete model-weight map

```text
MODEL CHECKPOINT = the trained recipe

┌──────────────────────────────────────────────────────────────┐
│ 1. TOKEN EMBEDDING TABLE                                     │
│    token ID → starting vector                                │
├──────────────────────────────────────────────────────────────┤
│ 2. TRANSFORMER LAYER 1                                       │
│    attention: WQ, WK, WV, output projection                  │
│    normalization weights                                      │
│    MLP/feed-forward weights                                   │
├──────────────────────────────────────────────────────────────┤
│ 3. TRANSFORMER LAYER 2                                       │
│    attention + normalization + MLP weights                    │
├──────────────────────────────────────────────────────────────┤
│                         ...                                   │
├──────────────────────────────────────────────────────────────┤
│ 4. TRANSFORMER LAYER 24                                      │
│    attention + normalization + MLP weights                    │
├──────────────────────────────────────────────────────────────┤
│ 5. OUTPUT WEIGHTS                                             │
│    final hidden vector → scores for the next token             │
└──────────────────────────────────────────────────────────────┘
```

One bread slice in more detail:

```text
hidden input
    │
    ├── normalization weights
    │
    ├── WQ ──► Q       ┌────────────────┐
    ├── WK ──► K ─────►│ attention      │
    └── WV ──► V ─────►│ Q compares K;  │
                        │ weighted V     │
                        └──────┬─────────┘
                               │
                 attention output projection
                               │
                        residual connection
                               │
                        normalization weights
                               │
                    MLP/feed-forward weights
                               │
                        residual connection
                               │
                        hidden output
```

The K/V cache is produced inside each slice using these weights:

```text
embedding + layer 1 weights  → K1/V1
hidden state + layer 2 weights → K2/V2
                              ...
hidden state + layer 24 weights → K24/V24
```

The weights are reused for every prompt, but the K/V values change for every
conversation and every processed token.

---

## 4. Same example in technical AI language

Example:

```text
Input: "I like tea"
Current token: "tea"
```

```text
token embeddings
      │
      ▼
┌─────────────────────────────────────────┐
│ TRANSFORMER LAYER                       │
│                                         │
│ 1. create Q, K, V                       │
│ 2. Q compares with K                    │
│ 3. softmax turns scores into percentages │
│ 4. percentages mix the V vectors        │
│ 5. residual + normalization              │
│ 6. MLP/feed-forward transformation      │
│ 7. residual + normalization              │
└─────────────────────────────────────────┘
      │
      ▼
improved hidden vectors → next layer
```

```text
tea embedding
     │
     ├── × WQ → Q(tea)
     ├── × WK → K(I), K(like), K(tea)
     └── × WV → V(I), V(like), V(tea)
                  │
                  ▼
          Q(tea) compares with every K
                  │
                  ▼
             attention scores
                  │
                  ▼
                softmax
                  │
                  ▼
        attention percentages × V
                  │
                  ▼
             attention output
```

Illustrative numbers:

```text
Q(tea) × K(I)       = 1.0
Q(tea) × K(like)    = 1.5
Q(tea) × K(tea)     = 2.0

softmax result:
I       → 20%
like    → 30%
tea     → 50%

attention result = 20% × V(I) + 30% × V(like) + 50% × V(tea)
```

Technical translation:

```text
look around       = self-attention
ask what matters  = Query (Q)
match information = Key (K)
carry information = Value (V)
think             = MLP/feed-forward network
learned habits    = model weights
worker            = transformer layer
24 workers        = 24 transformer layers
```

One layer passes its output to the next:

```text
embeddings
    ↓
Layer 1: Q/K/V → attention → MLP
    ↓
Layer 2: Q/K/V → attention → MLP
    ↓
...
    ↓
Layer 24: Q/K/V → attention → MLP
    ↓
output weights → next-token scores → next token
```

## 5. Attention calculation: Q × Kᵀ → softmax → V

Standard Transformer attention is:

```text
attention(Q, K, V) = softmax(Q × Kᵀ / √d) × V
```

Using the current token `tea`:

```text
Q(tea) = [1, 1]

K(I)    = [1, 0]
K(like) = [0, 1]
K(tea)  = [1, 1]
```

First compare Q with every K:

```text
Q × K(I)     = [1,1] · [1,0] = 1
Q × K(like)  = [1,1] · [0,1] = 1
Q × K(tea)   = [1,1] · [1,1] = 2

raw scores = [1, 1, 2]
```

Scale by the key dimension. Here `d = 2`:

```text
√d = √2 ≈ 1.414
scaled scores ≈ [0.707, 0.707, 1.414]
```

Softmax changes scores into percentages:

```text
softmax(xᵢ) = eˣⁱ / Σ eˣʲ

I       → 24.8%
like    → 24.8%
tea     → 50.3%
```

Now use those percentages to mix the Value vectors:

```text
V(I)    = [1, 0]
V(like) = [0, 1]
V(tea)  = [1, 1]

MATRIX FORM:

attention weights = [0.248  0.248  0.504]     shape: 1 × 3

V = [1  0]                                     shape: 3 × 2
    [0  1]
    [1  1]

weights × V
= [0.248  0.248  0.504] × [1  0]
                              [0  1]
                              [1  1]

attention output
= 24.8%×[1,0] + 24.8%×[0,1] + 50.3%×[1,1]
≈ [0.75, 0.75]
```

Zoom into the Value mixing:

```text
attention percentages          Value vectors

24.8% ───────────────────────► V(I)    = [1, 0]
24.8% ───────────────────────► V(like) = [0, 1]
50.3% ───────────────────────► V(tea)  = [1, 1]
   │                               │
   └──────────────┬────────────────┘
                  ▼
          WEIGHTED VALUE MIXER

first number:
  24.8%×1 + 24.8%×0 + 50.3%×1
  = 0.248 + 0.000 + 0.503
  ≈ 0.75

second number:
  24.8%×0 + 24.8%×1 + 50.3%×1
  = 0.000 + 0.248 + 0.503
  ≈ 0.75

ATTENTION OUTPUT = [0.75, 0.75]
```

Then the output continues through the rest of Layer 1:

```text
ATTENTION OUTPUT [0.75, 0.75]
              │
              ▼
      RESIDUAL CONNECTION
      add the original input
              │
              ▼
       NORMALIZATION
       keep numbers stable
              │
              ▼
          MLP ROOM
       transform the meaning
              │
              ▼
      RESIDUAL CONNECTION
      add the earlier signal
              │
              ▼
       NORMALIZATION
              │
              ▼
       OUTPUT OF LAYER 1
              │
              ▼
        INPUT TO LAYER 2
```

## 6. Complete transformer-layer walkthrough

### Plain-English overview: what the model is trying to do

Imagine writing a story one word at a time. Before choosing the next word, you
look at what you have already written so the new word fits the story.

```text
"I like tea"
       │
       ▼
the model asks: "What should come next, given everything so far?"
```

Inside each layer, the model performs four simple jobs:

```text
1. LOOK AROUND
   Attention asks: which earlier words matter right now?
   For "tea", it looks at "I", "like", and "tea".

2. KEEP THE ORIGINAL MEANING
   Residual connections add the new context to the original signal.
   Like adding spices without throwing away the meal.

3. TIDY THE NUMBERS
   Normalization keeps values in a healthy range so the next layer
   can work reliably.

4. THINK AND REFINE
   The MLP/feed-forward network transforms the combined information
   using learned weights.
```

The same work repeats through the stack:

```text
Layer 1   → basic word relationships
Layer 2   → improved local meaning
Layer 3   → more combined context
  ...
middle    → topic, relationships, and deeper patterns
  ...
Layer 24  → rich final representation
              │
              ▼
       output weights choose next-token probabilities
```

This is a teaching picture. Real models do not have one layer dedicated only
to grammar or one layer dedicated only to reasoning; useful patterns are
distributed across many layers.

This is a tiny hand-calculation for one token, `tea`. Real Qwen layers use
larger vectors, multiple heads, learned biases, and model-specific MLP
activation/order.

```text
1. Look around       → attention gathers context
2. Keep original     → residual preserves the input
3. Tidy numbers      → normalization stabilizes values
4. Think/refine      → MLP transforms the result
5. Keep original     → second residual preserves the signal
6. Tidy again        → second normalization
7. Pass upstairs     → output becomes Layer 2 input
```

```text
input x(tea)       = [1.0, 2.0]
attention output a = [0.75, 0.75]

RESIDUAL 1
x_res1 = x + a = [1.0, 2.0] + [0.75, 0.75] = [1.75, 2.75]

NORMALIZATION 1
mean = 2.25
variance = 0.25
standard deviation = 0.5
x_norm1 = [-1.0, 1.0]

MLP / FEED-FORWARD
W_mlp = [2  0]
        [1  1]
linear = [-1.0, 1.0] × W_mlp = [-1.0, 1.0]
ReLU(x) = max(0, x)
MLP output = [0.0, 1.0]

RESIDUAL 2
x_res2 = [-1.0, 1.0] + [0.0, 1.0] = [-1.0, 2.0]

NORMALIZATION 2
mean = 0.5
variance = 2.25
standard deviation = 1.5
layer output = [-1.0, 1.0]
```

```text
input x                 [1.0, 2.0]
    │
    ▼
attention output a      [0.75, 0.75]
    │
    ▼
residual 1              [1.75, 2.75]
    │
    ▼
normalization 1         [-1.0, 1.0]
    │
    ▼
MLP / feed-forward      [0.0, 1.0]
    │
    ▼
residual 2              [-1.0, 2.0]
    │
    ▼
normalization 2         [-1.0, 1.0]
    │
    ▼
Layer 1 output → Layer 2 input
```

`MLP` means **Multi-Layer Perceptron**. Attention gathers information from
other tokens; the MLP processes each token's gathered representation using
learned weights.

> Teaching note: this example uses ReLU and shows attention before the first
> normalization for clarity. Real Transformer implementations commonly use
> pre-normalization and GELU/SwiGLU-style MLPs, but the roles remain the same.

### Expanded worksheet: every calculation in one place

```text
STEP 0: INPUT EMBEDDING

x_tea = [1.0, 2.0]
attention output a_tea = [0.75, 0.75]
```

```text
STEP 1: LOOK AROUND

Q/K/V attention compares tea with I, like, and tea.
attention percentages: 25% I, 25% like, 50% tea (rounded teaching values)

a_tea = [0.75, 0.75]
```

```text
STEP 2: RESIDUAL CONNECTION 1

x_res1 = x_tea + a_tea
       = [1.0, 2.0] + [0.75, 0.75]
       = [1.75, 2.75]
```

```text
STEP 3: LAYER NORMALIZATION 1

mean = (1.75 + 2.75) / 2 = 2.25
variance = ((-0.5)² + (0.5)²) / 2 = 0.25
standard deviation = √0.25 = 0.5

first:  (1.75 - 2.25) / 0.5 = -1.0
second: (2.75 - 2.25) / 0.5 =  1.0

x_norm1 = [-1.0, 1.0]
```

```text
STEP 4: MLP / FEED-FORWARD

Option A: a matrix that produces zero after ReLU

W_mlp = [1  2]
        [0  1]

linear = [-1.0, 1.0] × W_mlp
       = [-1.0, -1.0]

ReLU([-1.0, -1.0]) = [0.0, 0.0]

Option B: an active teaching matrix

W_mlp = [2  0]
        [1  1]

linear = [-1.0, 1.0] × W_mlp
       = [-1.0, 1.0]

ReLU([-1.0, 1.0]) = [0.0, 1.0]
```

We use Option B for the remaining steps:

```text
STEP 5: RESIDUAL CONNECTION 2

x_res2 = x_norm1 + MLP output
       = [-1.0, 1.0] + [0.0, 1.0]
       = [-1.0, 2.0]
```

```text
STEP 6: LAYER NORMALIZATION 2

mean = (-1.0 + 2.0) / 2 = 0.5
variance = ((-1.5)² + (1.5)²) / 2 = 2.25
standard deviation = √2.25 = 1.5

first:  (-1.0 - 0.5) / 1.5 = -1.0
second: ( 2.0 - 0.5) / 1.5 =  1.0

x_out = [-1.0, 1.0]
```

```text
FINAL LAYER 1 SUMMARY

input x(tea)          [1.0, 2.0]
      ↓
attention output      [0.75, 0.75]
      ↓
residual 1            [1.75, 2.75]
      ↓
LayerNorm 1           [-1.0, 1.0]
      ↓
MLP                   [0.0, 1.0]
      ↓
residual 2            [-1.0, 2.0]
      ↓
LayerNorm 2           [-1.0, 1.0]
      ↓
Layer 1 output        [-1.0, 1.0]
      ↓
input to Layer 2
```

### After the layer: how one new answer token is created

After the final transformer layer, the model continues this loop:

```text
6. CREATE NEW HIDDEN VECTOR
   Layer 24 output becomes the current meaning vector
                         │
                         ▼
7. CALCULATE NEXT-TOKEN PROBABILITIES
   output weights compare the vector with vocabulary choices
                         │
                         ▼
   "the" → 40%     "is" → 30%     "and" → 10%     ...
                         │
                         ▼
8. SELECT A TOKEN
   selected token: "is"
                         │
                         ▼
9. CREATE K/V FOR THAT TOKEN
   K(is) and V(is) are calculated in every layer
                         │
                         ▼
10. APPEND TO THE CACHE
    old K/V + K(is), V(is)
                         │
                         ▼
    use the larger cache to generate the next token
```

Complete decode loop:

```text
old K/V cache
      │
      ▼
attention + MLP through all layers
      │
      ▼
new hidden vector
      │
      ▼
output weights → probabilities
      │
      ▼
select "is"
      │
      ▼
calculate K(is), V(is)
      │
      ▼
append K(is), V(is)
      │
      └───────────────┐
                      ▼
               generate next token
```

```text
Q(tea)
  │
  ├── compares with K(I)     → 24.8%
  ├── compares with K(like)  → 24.8%
  └── compares with K(tea)   → 50.3%
                                  │
                                  ▼
                    mix V(I), V(like), V(tea)
                                  │
                                  ▼
                         new meaning vector
```

Sigmoid is a different function:

```text
sigmoid(x) = 1 / (1 + e⁻ˣ)
sigmoid(2) ≈ 0.88
```

Sigmoid treats values independently. Standard attention uses softmax because
the attention percentages compete and add up to approximately 100%.

```text
softmax = competing attention percentages
sigmoid = independent strength between 0 and 1
```

### Master walkthrough: self-attention with `I like tea`

This is the complete calculation for the current token `tea`. The numbers are
small teaching values, not the full Qwen dimensions.

```text
Q = [1, 1]

K(I)    = [1, 0]
K(like) = [0, 1]
K(tea)  = [1, 1]

V(I)    = [1, 0]
V(like) = [0, 1]
V(tea)  = [1, 1]
```

#### 1. Matrix multiplication: `Q × Kᵀ`

```text
Q        = [1  1]                 shape: 1 × 2

Kᵀ       = [1  0  1]             shape: 2 × 3
           [0  1  1]

Q × Kᵀ   = [1  1  2]             shape: 1 × 3
```

The three scores correspond to:

```text
I:    1×1 + 1×0 = 1
like: 1×0 + 1×1 = 1
tea:  1×1 + 1×1 = 2
```

#### 2. Scaling

Standard scaled dot-product attention divides by `√dₖ`. Here `dₖ = 2`:

```text
√2 ≈ 1.414

[1, 1, 2] / 1.414
≈ [0.707, 0.707, 1.414]
```

#### 3. Softmax percentages

```text
softmax(xᵢ) = eˣⁱ / Σ eˣʲ

e⁰·⁷⁰⁷ ≈ 2.028
e⁰·⁷⁰⁷ ≈ 2.028
e¹·⁴¹⁴ ≈ 4.112

sum = 2.028 + 2.028 + 4.112 = 8.168

I:    2.028 / 8.168 ≈ 0.248 = 24.8%
like: 2.028 / 8.168 ≈ 0.248 = 24.8%
tea:  4.112 / 8.168 ≈ 0.503 = 50.3%
```

```text
attention percentages = [0.248, 0.248, 0.503]
```

#### 4. Mix the Value vectors

```text
attention percentages       Value matrix

[0.248  0.248  0.503]  ×  [1  0]
                            [0  1]
                            [1  1]
```

```text
V(I):    0.248 × [1,0] = [0.248, 0.000]
V(like): 0.248 × [0,1] = [0.000, 0.248]
V(tea):  0.503 × [1,1] = [0.503, 0.503]

first number:  0.248 + 0.000 + 0.503 = 0.751
second number: 0.000 + 0.248 + 0.503 = 0.751

ATTENTION OUTPUT ≈ [0.75, 0.75]
```

The complete formula is:

```text
Attention(Q,K,V) = softmax(Q × Kᵀ / √dₖ) × V
```

### Matrix-layout clarification

In this teaching example, the key vectors are placed as **columns**, so the
calculation is written as `Q × K`:

```text
Q = [1  1]                         shape: 1 × 2

K(I)    = [1]       K(like) = [0]       K(tea) = [1]
          [0]                [1]                [1]

K = [1  0  1]                       shape: 2 × 3
    [0  1  1]

Q × K = [1  1] × [1  0  1]
                  [0  1  1]
      = [1  1  2]                   shape: 1 × 3
```

Same matrices as visible boxes:

```text
Q = ┌─────┬─────┐
    │  1  │  1  │  row 1
    └─────┴─────┘
       col1  col2
```

```text
K = ┌─────┬─────┬─────┐
    │  1  │  0  │  1  │  row 1
    ├─────┼─────┼─────┤
    │  0  │  1  │  1  │  row 2
    └─────┴─────┴─────┘
       col1  col2  col3
        I    like   tea
```

```text
Q × K = ┌─────┬─────┬─────┐
         │  1  │  1  │  2  │  row 1
         └─────┴─────┴─────┘
            I    like   tea
```

```text
I:    (1×1) + (1×0) = 1
like: (1×0) + (1×1) = 1
tea:  (1×1) + (1×1) = 2
```

Many textbooks store key vectors as rows. Then the same calculation is written
as `Q × Kᵀ`:

```text
K_rows = [1  0]
         [0  1]
         [1  1]                       shape: 3 × 2

Q × K_rowsᵀ = [1  1] × [1  0  1]
                           [0  1  1]
             = [1  1  2]
```

Both layouts produce the same score vector. The inner dimensions must match,
and the result contains one score for each token.

```text
Q × Kᵀ → raw similarities
      ↓
divide by √dₖ → stable scores
      ↓
softmax → attention percentages
      ↓
percentages × V → contextual meaning vector
```

## 6. Transformer as a 3D building

Imagine the model as a 24-floor building. Each floor is one transformer layer.

```text
                              ROOF
                    next-token scores/output
                         ┌──────────────┐
                        /  FLOOR 24    /│
                       / attention    / │
                      / + MLP        /  │
                     └──────────────┘   │
                     │ hidden state  │   │
                     └──────────────┘  /
                         ┌──────────────┐
                        /  FLOOR 3     /│
                       / attention    / │
                      / + MLP        /  │
                     └──────────────┘   │
                     │ hidden state  │   │
                     └──────────────┘  /
                         ┌──────────────┐
                        /  FLOOR 2     /│
                       / attention    / │
                      / + MLP        /  │
                     └──────────────┘   │
                     │ hidden state  │   │
                     └──────────────┘  /
                         ┌──────────────┐
                        /  FLOOR 1     /│
                       / attention    / │
                      / + MLP        /  │
                     └──────────────┘   │
                     │ token vectors │   │
                     └──────────────┘  /
                           FOUNDATION
                    BOS, I, like, tea vectors
```

Each floor has two main rooms:

```text
┌──────────────────────────────────────────┐
│ ONE FLOOR = ONE TRANSFORMER LAYER        │
│                                          │
│ ATTENTION ROOM                           │
│   Q asks: what should I look at?         │
│   K says: what does each token offer?    │
│   V carries: what information is useful? │
│                                          │
│ MLP ROOM                                 │
│   transforms the collected information   │
│                                          │
│ PIPE TO NEXT FLOOR                       │
│   passes the improved hidden vector      │
└──────────────────────────────────────────┘
```

The building also has two different kinds of storage:

```text
BLUEPRINT ROOM                         TEMPORARY NOTE ROOM
model weights                          K/V cache
WQ, WK, WV, MLP weights                K and V for this prompt
learned during training                created during inference
used on every request                  changes for every conversation
```

### Small hand-calculation inside one floor

These are teaching numbers, not the full Qwen dimensions.

```text
Current token: tea

Q(tea) = [1, 1]
K(I)   = [1, 0]       V(I)    = [1, 0]
K(like)= [0, 1]       V(like) = [0, 1]
K(tea) = [1, 1]       V(tea)  = [1, 1]
```

The attention room compares Q with every K:

```text
Q · K(I)    = 1×1 + 1×0 = 1
Q · K(like) = 1×0 + 1×1 = 1
Q · K(tea)  = 1×1 + 1×1 = 2
```

Softmax changes the scores into attention percentages:

```text
score 1 → about 21%
score 1 → about 21%
score 2 → about 58%
```

The room then mixes the V information:

```text
attention output
= 21%×[1,0] + 21%×[0,1] + 58%×[1,1]
≈ [0.79, 0.79]
```

That output goes through the MLP room and then travels upstairs:

```text
Q/K/V calculation
        ↓
attention output [0.79, 0.79]
        ↓
MLP transforms it
        ↓
Floor 1 output → Floor 2 input → ... → Floor 24
```

The K/V cache is like keeping the room notes for every floor:

```text
Floor 1:  K1/V1 for old tokens
Floor 2:  K2/V2 for old tokens
   ...
Floor 24: K24/V24 for old tokens
```

DecaState can save those local notes and restore them later. It does not save
the building blueprint—the model weights are already in the model checkpoint.

### One transformer layer, zoomed in

```text
COMMON LANGUAGE                         TECHNICAL NAME

look around at other words       →      Q/K/V attention
keep original understanding     →      residual connection
tidy and stabilize numbers      →      normalization
think about what was found      →      MLP/feed-forward network
```

Using `I like tea`:

```text
INPUT: hidden vector for "tea"
                         │
                         ▼
┌────────────────────────────────────────┐
│ 1. LOOK AROUND                         │
│    Which words matter to tea?          │
│    Q(tea) compares with K(I),          │
│    K(like), and K(tea).                │
│    percentages mix V(I), V(like),     │
│    and V(tea).                         │
└───────────────────┬────────────────────┘
                    ▼
             attention output
                    │
                    ▼
┌────────────────────────────────────────┐
│ 2. KEEP THE ORIGINAL                   │
│    add the original input back         │
│    so useful information is not lost   │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│ 3. TIDY THE NUMBERS                    │
│    normalization keeps values stable   │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│ 4. THINK ABOUT THE RESULT              │
│    MLP transforms the meaning          │
│    using learned weights               │
└───────────────────┬────────────────────┘
                    ▼
             improved "tea" vector
                    │
                    ▼
                next layer
```

```text
Q/K/V attention
       +
residual connection + normalization
       +
MLP/feed-forward network
       = ONE TRANSFORMER LAYER
```

### Isometric view of one floor

Ignore the other 23 floors for a moment. One transformer floor looks like this:

```text
                 ONE TRANSFORMER FLOOR
                    ISOMETRIC VIEW

                         OUTPUT TO FLOOR 2
                              ▲
                              │
        ┌─────────────────────┴─────────────────────┐
       /│                                            /│
      / │              MLP ROOM                    / │
     /  │       transforms information             /  │
    └───┼─────────────────────────────────────────┘   │
    │   │                                             │
    │   │          RESIDUAL + NORMALIZATION           │
    │   └─────────────────────────────────────────────┘
    │  /                                              /
    │ /          ATTENTION ROOM                      /
    │/     Q compares with K; selects V             /
    └──────────────────────────────────────────────┘
     │                                             │
     │           Q / K / V SPLITTER                │
     └─────────────────────────────────────────────┘
      ▲
      │
 INPUT TOKENS
 BOS, I, like, tea
```

The machine line inside the floor is:

```text
INPUT → Q/K/V SPLITTER → ATTENTION ROOM → MLP ROOM → OUTPUT
```

```text
tea vector
   │
   ├── WQ → Q(tea)
   ├── WK → K(tea)
   └── WV → V(tea)
```

The side storage attached to the floor is the K/V cache:

```text
                 ┌──────────────────────────┐
                 │ ATTENTION FLOOR          │
                 │ Q/K/V + MLP              │
                 └─────────────┬────────────┘
                               │
                               ▼
                 ┌──────────────────────────┐
                 │ K/V STORAGE RACK         │
                 │                          │
                 │ K(BOS), V(BOS)           │
                 │ K(I),   V(I)             │
                 │ K(like),V(like)          │
                 │ K(tea), V(tea)            │
                 └──────────────────────────┘
```

The complete building repeats this same floor 24 times:

```text
FLOOR 24: attention + MLP + K/V rack
    ▲
FLOOR 3:  attention + MLP + K/V rack
    ▲
FLOOR 2:  attention + MLP + K/V rack
    ▲
FLOOR 1:  attention + MLP + K/V rack
    ▲
token embeddings
```

## 7. “I like tea” → next question, side by side

Assume the second request continues the same conversation:

```text
Request 1: "I like tea"
Request 2: "Why do I like it?"
```

| Stage | Request 1: first reading | Request 2: continuing conversation |
|---|---|---|
| Input | `BOS, I, like, tea` | old conversation + `Why, do, I, like, it, ?` |
| Embeddings | create vectors for all first tokens | reuse old state; create vectors for new tokens |
| Q/K/V | create Q, K, V for `BOS, I, like, tea` | create Q, K, V for new tokens; old K/V already exists |
| Attention | `Q(tea)` compares with earlier `K` values | each new query compares with old K/V plus new K/V |
| MLP | transforms the attention result | transforms the new attention result |
| Cache | save K/V for every layer and token | append new K/V to every layer |
| Work avoided | none on the first request | old prompt prefill can be skipped if state is valid |
| Output | predicts the next token | predicts the answer to the new question |

```text
REQUEST 1: BUILD THE BUILDING NOTES

I ──► embedding ──► Layer 1 Q/K/V ──► Layer 2 ──► ... ──► Layer 24
like ─► embedding ─► Layer 1 Q/K/V ──► Layer 2 ──► ... ──► Layer 24
tea ─► embedding ──► Layer 1 Q/K/V ──► Layer 2 ──► ... ──► Layer 24
                                                        │
                                                        ▼
                                      save K/V notes for old tokens
```

```text
REQUEST 2: USE OLD NOTES + ADD NEW TOKENS

old K/V notes for: BOS, I, like, tea
                │
                ├──────────────────────────────┐
                │                              │
                ▼                              ▼
        reuse old K/V                 new question tokens
                                               │
                                               ▼
                                    create new Q/K/V
                                               │
                ┌──────────────────────────────┘
                ▼
new Q compares with old K and new K
                │
                ▼
attention → MLP → append new K/V → answer
```

One new-token calculation looks like this:

```text
new token: "it"
     │
     ├── Q(it) asks what matters
     ├── compares with K(BOS), K(I), K(like), K(tea)
     ├── compares with K(Why), K(do), K(I), K(like), K(it)
     ├── uses the selected V information
     └── passes the result through the MLP
```

The old K/V is not an answer. It is numerical attention state that lets the
new question look back at the earlier conversation without rebuilding it.

## 7. Prefix: what part can be reused?

## 8. API Provider GPU–K/V Cache: How They Work Together

For an API model, the GPU, model weights, inference runtime, and K/V cache
operate as one provider-side inference machine. They are not separate LLMs
talking to one another.

```text
YOUR COMPUTER
Claude Code / Codex / application
        |
        | HTTPS request
        v
PROVIDER API FRONT DOOR
        |
        v
REQUEST ROUTER
        |
        v
MODEL INFERENCE RUNTIME
        |
        +-- model weights
        +-- GPU memory
        +-- K/V cache
        +-- GPU computation kernels
        |
        v
generated response
```

Inside provider GPU memory:

```text
┌─────────────────────────────────────────────┐
│ PROVIDER GPU MEMORY                         │
│                                             │
│ model weights: WQ, WK, WV, MLP weights      │
│ K/V cache: K and V for old tokens           │
│ activations: current token calculations     │
└─────────────────────────────────────────────┘
```

### First request: creating the provider cache

```text
full prompt: system + tools + files + question
                         |
                         v
GPU PREFILL
  read model weights
  calculate embeddings
  calculate Q/K/V
  perform attention
  write K/V into GPU memory
                         |
                         v
              K/V cache for the prompt
                         |
                         v
                    generate answer
```

### Finding the next token

If the model has processed `I like tea`, the cache contains:

```text
K(I), V(I)
K(like), V(like)
K(tea), V(tea)
```

The next-token loop is:

```text
OLD K/V CACHE
      |
      | GPU reads old K/V
      v
create Q for current position
      |
      v
Q compares with K(I), K(like), K(tea)
      |
      v
attention percentages select/mix V values
      |
      v
new hidden state → next-token probabilities
      |
      v
choose next token: "is"
      |
      v
calculate K(is), V(is)
      |
      v
append K(is), V(is) to the cache
      |
      v
repeat for the next token
```

Without a cache, the old prompt would be recomputed for every new output
token. With a cache, the GPU reads old K/V, computes the current position, and
appends only the new K/V.

```text
WITHOUT CACHE                  WITH CACHE
recompute old prompt           read old K/V
        |                              |
        v                              v
generate next token            compute current token
        |                              |
        v                              v
repeat                          append new K/V
                                       |
                                       v
                                    repeat
```

### Provider prompt-cache lookup

For a later API request:

```text
same system + tools + files + new question
                         |
                         v
              provider cache manager
                         |
                    +----+----+
                    |         |
                   HIT       MISS
                    |         |
               reuse K/V    prefill prefix
                    |         |
                    +----+----+
                         v
                 process new question
                         |
                         v
                    generate answer
```

DecaState does not directly see or control the provider tensors. It can make
the prefix stable, route the request, and measure provider-reported usage. The
provider inference runtime loads/reuses K/V, and the GPU reads old K/V and
writes new K/V.

```text
model weights → GPU calculations → K/V cache
                                      ↑     │
                                      │     │
                         GPU reads old     │
                         GPU appends new ──┘
```

### Detailed ASCII: the complete provider-side loop

```text
YOUR COMPUTER
Claude Code / Codex / application
        │
        │ HTTPS request:
        │ system + tools + files + question
        ▼
PROVIDER API FRONT DOOR
        │
        ▼
REQUEST ROUTER
        │
        ▼
MODEL INFERENCE RUNTIME
        │
        ├── model weights
        ├── GPU memory
        ├── K/V cache
        └── GPU computation kernels
        │
        ▼
PROVIDER GPU
        │
        ├── tokenizer: text → token IDs
        ├── embeddings: IDs → vectors
        ├── transformer layers
        ├── attention: Q × K → weights → V
        ├── prefill: create/read K/V state
        └── decode: generate answer tokens
        │
        ▼
RESPONSE + USAGE DATA
        │
        ▼
YOUR COMPUTER
```

```text
PROVIDER GPU MEMORY

┌─────────────────────────────────────────────┐
│ MODEL WEIGHTS                               │
│ WQ, WK, WV, MLP, normalization, output     │
├─────────────────────────────────────────────┤
│ K/V CACHE                                   │
│ K and V for previously processed tokens     │
├─────────────────────────────────────────────┤
│ TEMPORARY ACTIVATIONS                       │
│ current token calculations                  │
└─────────────────────────────────────────────┘
```

```text
FIRST REQUEST: CREATE THE PROVIDER K/V CACHE

full prompt
system + tools + files + question
        │
        ▼
GPU PREFILL
        │
        ├── read model weights
        ├── calculate embeddings
        ├── calculate Q/K/V
        ├── perform attention
        └── write K/V into GPU memory
        │
        ▼
K/V CACHE FOR THE PROMPT
        │
        ▼
GENERATE ANSWER
```

```text
NEXT TOKEN LOOP

OLD K/V CACHE
I, like, tea
        │
        │ GPU reads old K/V
        ▼
CREATE Q FOR CURRENT POSITION
        │
        ▼
Q compares with:
K(I), K(like), K(tea)
        │
        ▼
attention percentages
        │
        ▼
mix selected V values:
V(I), V(like), V(tea)
        │
        ▼
new hidden state
        │
        ▼
next-token probabilities
        │
        ▼
choose next token: "is"
        │
        ▼
calculate K(is), V(is)
        │
        ▼
append K(is), V(is) to the cache
        │
        ▼
repeat for the next token
```

```text
WITHOUT CACHE                  WITH CACHE

recompute old prompt           read old K/V
        │                              │
        ▼                              ▼
generate next token            compute current token
        │                              │
        ▼                              ▼
repeat                          append new K/V
                                       │
                                       ▼
                                    repeat
```

```text
LATER API REQUEST

same system + tools + files + new question
        │
        ▼
PROVIDER CACHE MANAGER
        │
   ┌────┴────┐
   │         │
  HIT       MISS
   │         │
reuse      prefill
old K/V    full prefix
   │         │
   └────┬────┘
        ▼
process new question
        │
        ▼
generate answer
```

```text
THE GPU/CACHE CONNECTION

model weights → GPU calculations → K/V cache
                                      ↑     │
                                      │     │
                         GPU reads old     │
                         GPU appends new ──┘
```

The provider runtime is the coordinator. The model does not independently
decide to reuse memory; the runtime supplies old K/V to the GPU and tells the
GPU where to append new K/V.

A prefix is the beginning of a request that remains unchanged.

```text
[system instructions + repository files] + [new question]
\_______________________________/       \____________/
             stable prefix                 new part
```

Example:

```text
SYSTEM: You are a coding assistant.
REPOSITORY: README.md, src/login.py, tests/test_login.py
QUESTION 1: Find the login bug.
```

The reusable prefix is:

```text
SYSTEM + REPOSITORY
```

The new part is:

```text
QUESTION 1
```

On the next request:

```text
SYSTEM + REPOSITORY + QUESTION 2
```

Only the question changed, so the prefix may be reusable.

The exact cache boundary depends on the runtime/provider. Changing tools,
system instructions, model version, or earlier serialized content can cause a
cache miss.

---

## 4. Prefill and decode

### Prefill

Prefill means the model reads the existing input context and creates K/V state.

```text
old prompt tokens
      |
      v
GPU/accelerator reads all tokens
      |
      v
creates K/V attention state
```

### Decode

Decode means generating the answer one token at a time.

```text
existing K/V + new token position
              |
              v
        predict next token
              |
              v
        predict next token
              |
              v
              ...
```

The main saving is avoiding repeated **old-context prefill**. The new question
still needs processing, and the answer still needs generation.

### How the prefix and prefill are connected

The prefix is the reusable input. Prefill is the computation that turns that
input into reusable K/V attention state.

```text
PREFIX = the beginning of the input
PREFILL = reading input tokens and creating K/V state

[stable prefix] + [new question]
       |
       +-- first request: prefill both parts
       |
       +-- later request: reuse prefix K/V,
                          prefill only the new part
```

First request:

```text
system + repository + question 1
              |
              v
        PREFILL ALL INPUT
              |
              v
        create K/V state
              |
              v
        generate answer 1
```

Later request with the same prefix:

```text
same prefix  -----------------> already computed K/V
new question -----------------> prefill only this part
                                      |
                                      v
                         old K/V + new K/V -> answer 2
```

Illustrative token accounting:

```text
WITHOUT REUSE
100,000 old tokens + 50 new tokens -> prefill 100,050 tokens

WITH VALID PREFIX STATE
0 old tokens recomputed + 50 new tokens -> prefill 50 new tokens
```

If the prefix changes in the middle, only the unchanged beginning may remain
reusable:

```text
[system] [tools] [old file] [question]
\________ reusable _______/

[system] [tools] [new file] [question]
\______ reusable _____/   \__ prefill again __/
```

The runtime—not the model—decides which prefix is eligible. For local MLX,
DecaState validates the model, tokenizer, fingerprint, position, and cache
before restoring K/V. For an API model, DecaState sends a stable prefix, but
the provider makes the final cache-hit decision.

### Prefill versus decode: two different kinds of work

```text
PREFILL = read the input prompt
DECODE  = write the answer, one token at a time

INPUT PROMPT                              OUTPUT ANSWER
system + repo + question                  token 1 -> token 2 -> token 3 -> ...
        |                                  
        v                                  
   PREFILL PHASE                    DECODE PHASE
   process many input tokens        process each new output token
   create K/V state                 append each token to K/V state
```

Example:

```text
Input:  100,000 tokens
Output: 500 tokens

PREFILL: 100,000 input tokens become K/V state
DECODE:  500 answer tokens are generated one by one
```

With a valid prefix cache:

```text
WITHOUT CACHE
old 100,000 input tokens -> prefill again
new question              -> prefill
500 answer tokens         -> decode

WITH CACHE
old 100,000 input tokens -> reuse old K/V
new question             -> prefill
500 answer tokens        -> decode
```

Prefix caching saves repeated input processing. It does not automatically make
output tokens free or eliminate the work of generating the answer.

```text
TOKEN / COST MAP

old input tokens  -> cache can reduce repeated processing/cost
new input tokens  -> still processed
output tokens     -> still generated; usually still billed
reasoning tokens  -> provider/model-specific
```

Possible saving levers:

```text
1. Stable prefix caching  -> avoid repeated old-input prefill
2. Local K/V restore      -> skip old prefill after process death
3. Smaller new context    -> send fewer files and tool outputs
4. Shorter answer policy  -> generate fewer output tokens when suitable
5. Speculative decoding   -> may improve local speed; billing is provider-specific
```

DecaState should report these separately, rather than one misleading number:

```text
input tokens avoided:       100,000
output tokens generated:        500
provider saving:            verified / unknown
answer quality:             measured separately
```

### Local MLX example: inspect the saved state

From the DecaState repository:

```bash
cd /Users/ashish/DECASTATE
find .decastate -name "native-cache.safetensors" -o -name "manifest.json"
```

`<STATE_ID>` is a placeholder. Replace it with a real directory returned by
the `find` command. For example, this repository currently contains
`coding-demo-1787535612330`:

```bash
python -m json.tool .decastate/states/coding-demo-1787535612330/manifest.json
```

It can describe the model, token count, cache position, and fingerprint.
`native-cache.safetensors` is a binary tensor file containing the actual local
K/V arrays. Inspect it with MLX/SafeTensors tooling, not `cat`:

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

The local decision flow is:

```text
load manifest.json
      |
      +-- same model and tokenizer?
      +-- same fingerprint?
      +-- valid cache position?
      +-- cache file readable?
      |
   all pass
      |
      v
restore native K/V -> skip old prefix prefill -> continue

any check fails
      |
      v
reject restore -> prefill the full input again
```

This is different from an API model: local DecaState can directly validate,
load, and restore its own native K/V tensors. The API provider's K/V tensors
remain private on the provider's infrastructure.

---

## 5. API model: cache hit and cache miss

The language model does not decide whether the cache is reused. The provider's
serving/cache layer makes that decision before or around inference.

```text
YOUR COMPUTER
  prompt
    |
    v
Claude Code / Codex client / application
    |
    v
optional DecaState gateway
    |
    v  HTTPS
PROVIDER CACHE MANAGER
    |
    +-- Does the stable prefix match?
```

### API cache miss

```text
prefix not found
      |
      v
provider prefills the old prefix
      |
      v
provider processes the new question
      |
      v
provider generates a new answer
```

### API cache hit

```text
prefix matches
      |
      v
provider reuses its private K/V state
      |
      v
provider processes the new question
      |
      v
provider generates a new answer
```

The provider owns its model weights, GPU/accelerator, and raw K/V tensors.
DecaState can route the request and read usage fields, but cannot download the
provider's private K/V tensors.

---

## 6. Local MLX model: DecaState restore

For a local model, DecaState can control the restore decision directly.

### Process A: create the state

```text
PROCESS A
  load model weights
      |
      v
  prefill system + repository
      |
      v
  MLX creates K/V tensors
      |
      v
  DecaState saves native-cache.safetensors
      |
      v
  Process A exits
```

### Process B: resume the state

```text
PROCESS B
  load the same model weights
      |
      v
  check model/runtime fingerprint
      |
      v
  load native-cache.safetensors
      |
      v
  process only the new question
      |
      v
  generate the new answer
```

```text
Process A RAM: destroyed
Saved file:   remains on disk
Process B:    restores K/V and continues
```

“Process death” means Process A really exits. Its memory and process ID are
gone. The proof is that Process B is a separate operating-system process and
can continue from the saved file.

---

## 7. Q, K, and V in simple terms

```text
Q = Query  -> what the current token is looking for
K = Key    -> signals describing earlier tokens
V = Value  -> information carried by earlier tokens
```

The model creates them using learned model weights:

```text
hidden state
     |
     +-- x WQ -> Q
     +-- x WK -> K
     +-- x WV -> V
```

Attention then asks:

```text
Which earlier information is useful for the current token?
```

```text
new Q
  |
  +-- compare with previous K
  |
  +-- create relevance percentages
  |
  +-- use those percentages to mix previous V
  |
  v
information used to predict the next token
```

The actual K and V are floating-point arrays, not English labels. The labels
are only a teaching analogy.

---

## 8. Where does the saving happen?

### Local model

```text
Without restore:
  GPU recomputes old-context prefill
  GPU generates new answer

With DecaState restore:
  load old K/V from disk
  skip old-context prefill
  GPU generates new answer
```

Saving:

```text
local GPU work
latency
energy
repeated computation
```

### API model

```text
Without provider cache:
  old input is processed and billed normally

With provider cache:
  old input is reused and billed as cached input
  new question and output are still billed normally
```

Saving:

```text
provider input-token cost
```

An API token is mainly a billing/accounting unit for input and output text. It
is not literally a GPU electricity unit, although more tokens generally mean
more computation. Providers may also report cached input, reasoning, tool, or
search usage separately.

---

## 9. What does “token cost” mean?

An API provider counts different work categories separately. A token is a
small piece of text according to that model's tokenizer. It is both an input
unit for the model and an accounting unit on the provider bill.

```text
YOUR REQUEST
  system instructions       -> input tokens
  repository/files           -> input tokens
  user question              -> input tokens
  cached repeated prefix     -> cached input tokens

MODEL WORK
  visible answer             -> output tokens
  hidden reasoning (if used) -> reasoning tokens
  tool/search/file content   -> tool or input tokens
```

The conceptual bill is:

```text
TOTAL API COST
  = normal input-token cost
  + cached-input cost
  + output-token cost
  + reasoning/tool/search charges when applicable
```

```text
WITHOUT CACHE
  old context: normal input price
  new question: normal input price
  answer:       output price

WITH CACHE
  old context: cached-input price
  new question: normal input price
  answer:       output price
```

The cache does not make the new answer free. It discounts only the repeated
input portion when the provider reports a cache hit.

---

## 10. Model weights create the temporary K/V state

Weights are permanent learned numbers. Q/K/V are temporary numbers calculated
from those weights for the current context.

```text
PERMANENT MODEL WEIGHTS
  WQ, WK, WV, plus all other neural-network weights
              |
              v
TOKEN EMBEDDING / HIDDEN STATE
              |
              +-- multiply by WQ -> Q
              +-- multiply by WK -> K
              +-- multiply by WV -> V
              |
              v
        attention calculation
              |
              v
       temporary K/V cache state
```

```text
weights = what the model learned during training
K/V      = what the model has processed in this conversation
```

The model creates Q/K/V inside every transformer layer. DecaState does not
invent them; it saves and restores the K/V arrays after MLX creates them.

---

## 11. One request versus the next request

```text
REQUEST 1

[system + repository + question 1]
 \___________ prefill all __________/
               |
               v
          create old K/V
               |
               v
          generate answer 1


REQUEST 2

[system + repository] + [question 2]
 \_____ stable prefix ____/   \new/
             |
             v
       cache manager checks prefix
             |
        +----+----+
        |         |
       HIT       MISS
        |         |
   reuse old   prefill old
      K/V      prefix again
        |         |
        +----+----+
             |
             v
       process question 2
             |
             v
       generate answer 2
```

The model never says “I already know the answer.” The cache manager says “I
already have the attention state for this prefix.” The new question still
enters the model, and the answer is generated again.

The complete connection is:

```text
PREFIX
  |
  |  prefill computes attention for these tokens
  v
K/V CACHE
  |
  |  later request reuses this state
  v
NEW QUESTION
  |
  |  runtime computes only the new portion
  v
DECODE -> answer
```

---

## 12. Local and API paths side by side

```text
LOCAL MLX + DECASTATE                 API MODEL
----------------------                ----------------------
prompt on your computer               prompt on your computer
          |                                      |
          v                                      v
local tokenizer                         client / gateway
          |                                      |
          v                                      v
local model weights                     HTTPS over internet
          |                                      |
          v                                      v
Apple GPU + MLX                         provider cache manager
          |                                      |
          v                                      +-- hit: provider reuses K/V
create K/V                              +-- miss: provider prefills
          |                                      |
          v                                      v
save native-cache.safetensors           provider GPU creates/uses K/V
          |                                      |
          v                                      v
Process B restores                      answer + usage fields returned
```

```text
LOCAL K/V:  DecaState can save, inspect, fingerprint, and restore it.
API K/V:    provider owns it; DecaState receives usage, not tensors.
```

## 13. Process A / Process B: local versus API

The word “restore” means something different in these two worlds.

### Local MLX: DecaState directly restores the native K/V file

```text
PROCESS A: local save                         PROCESS B: local wake
---------------------                         --------------------
load model weights                            load same model weights
        |                                             |
        v                                             v
prefill repository + question                read manifest.json
        |                                             |
        v                                             v
MLX creates native K/V                       validate model/fingerprint
        |                                             |
        v                                             v
save native-cache.safetensors                load native K/V tensors
        |                                             |
        v                                             v
Process A exits                               skip old prefix prefill
                                                     |
                                                     v
                                              process new question
                                                     |
                                                     v
                                              continue generation
```

Process A and Process B are separate operating-system processes. The local
DecaState runtime owns the saved file and can directly validate and restore it.

### Claude/OpenAI API: the provider owns the K/V cache

```text
PROCESS A: first API request                  PROCESS B: later API request
----------------------------                  ----------------------------
build stable prefix                           build the same stable prefix
        |                                             |
        v                                             v
DecaState can count/hash it                    DecaState can count/hash it
        |                                             |
        v                                             v
send HTTPS request                             send HTTPS request
        |                                             |
        v                                             v
provider prefill                               provider checks its cache
        |                                             |
        v                                      +------+------+
provider creates private K/V                  |             |
        |                                    HIT           MISS
        v                                      |             |
provider returns answer                 reuse private   prefill prefix
                                           provider K/V    again
                                                   \       /
                                                    v     v
                                                  new question
                                                       |
                                                       v
                                                 provider answer
```

Process B does not download or restore the provider's K/V file. The provider's
own serving system decides whether its private cache is still available and
whether the prefix matches. DecaState can make the prefix stable, add
provider-supported cache controls, measure the returned usage fields, and
explain the result—but it cannot force a provider hit.

### How the state grows from Question 1 to Question 10

When a conversation continues, the K/V state grows by appending new tokens.
The old state is not recalculated just because a new question was added.

```text
Question 1:
SYSTEM + REPO + Q1 + ANSWER1
\──────────── K/V state 1 ────────────/

Question 2:
SYSTEM + REPO + Q1 + ANSWER1 + Q2 + ANSWER2
\────────────────── K/V state 2 ──────────────────/

Question 10:
SYSTEM + REPO + Q1 ... + Q9 + ANSWER9 + Q10
\──────────────────────── K/V state 10 ────────────────────────/

K/V state 10 = K/V state 1 + new K/V for later questions and answers
```

For Question 10:

```text
old K/V through Question 9 -> reuse old state
Question 10                 -> compute new tokens
old K/V + new K/V           -> answer 10
```

If an earlier message changes, reuse stops at that point:

```text
Q1 + Q2 + Q3 + Q4 + Q5
\──────── valid cached prefix ────────/

Q1 + Q2 + Q3 CHANGED + Q4 + Q5
\──── reusable ────/ \── recompute ──/
```

```text
new question appended  -> reuse old K/V and extend it
earlier message edited  -> recompute from the changed point
model changed           -> old K/V invalid; prefill everything
```

For API models, the provider may reuse the longest matching prefix if its
private cache still exists. For local MLX, DecaState can directly maintain and
extend the native K/V state.

```text
LOCAL MLX                         CLAUDE / OPENAI API
---------                         ------------------
DecaState owns K/V                provider owns K/V
DecaState validates restore       provider decides hit/miss
DecaState loads tensors           DecaState sends request
local GPU computes continuation   provider GPU computes continuation
local file proves restore         usage fields prove reported reuse
```

So both sides have a “cache manager,” but they have different authority:

```text
Local cache manager:  direct control over native state
Provider cache:       provider-controlled reuse decision
DecaState API layer:  prefix preparation + routing + measurement + evidence
```

---

## 13. Full zoomed flow

```text
1. USER TYPES
   "Explain the login bug"
        |
        v
2. TOKENIZER
   text -> model-specific token pieces -> token IDs
        |
        v
3. EMBEDDING LOOKUP
   token IDs -> vectors of numbers
        |
        v
4. TRANSFORMER LAYER
   hidden vectors -> Q/K/V using learned weights
        |
        v
5. ATTENTION
   Q compares with K -> percentages -> weighted V
        |
        v
6. PREFILL / KV STATE
   old input becomes reusable K/V state
        |
        +------------------------------+
        |                              |
        v                              v
7A. LOCAL SAVE                     7B. API CACHE
    DecaState writes file              provider keeps private cache
        |                              |
        v                              v
8. NEW QUESTION                    8. NEW QUESTION
    load old K/V + new tokens          provider hit/miss + new tokens
        |                              |
        +--------------+---------------+
                       v
9. DECODE
   generate one new answer token at a time
                       |
                       v
10. RESPONSE
    answer returns to the user
```

---

## 14. Ownership summary

```text
DecaState local runtime:
  chooses whether to load local state
  validates fingerprints
  saves/restores native MLX K/V

Provider cache manager:
  chooses API cache hit or miss
  owns server-side K/V state
  reports usage and pricing categories

LLM model:
  creates Q/K/V using learned weights
  performs attention
  generates the answer

User:
  writes the prompt and receives the answer
```

## 15. Toy LLM progress map

This section is the permanent checklist for the small learning model. It is
separate from the real Qwen/MLX experiments so we never confuse a teaching
machine with the production model.

### Completed

```text
Step 1  text -> tokens -> embeddings
Step 2  embeddings -> Q/K/V
Step 3  Q/K/V -> attention percentages -> weighted V
Step 4  attention -> residual -> normalization -> MLP
Step 5  layer output -> logits -> next-token probabilities
Step 6  loss -> gradients -> weight updates
Step 7  train tiny model -> freeze weights -> inference
Step 8  fine-tuning memory -> mitigation choices
Step 9  multiple transformer layers
Step 10 train toy Q/K/V attention weights
Step 11 generate tokens one at a time
Step 12 save/restore toy K/V cache
```

The code and lessons are:

```text
experiments/08_step1_tokens_embeddings.py
Experiment/02_embeddings_qkv.py
Experiment/03_attention.py
Experiment/04_transformer_layer.py
Experiment/05_logits_next_token.py
Experiment/06_training_loss_backprop.py
Experiment/07_tiny_train_then_infer.py
Experiment/08_finetuning_memory.py
Experiment/09_multi_layer_forward.py
Experiment/10_train_qkv_attention.py
Experiment/11_tiny_generation_loop.py
Experiment/12_toy_kv_cache_save_restore.py
```

Run them with:

```bash
make step1
make step2
make step3
make step4
make step5
make step6
make step7
make step8
make step9
make step10
make step11
make step12
```

### What we have now

```text
We have a transparent toy LLM-like learning path.
We can show training changing weights.
We can freeze those weights and run inference.
We understand the main vocabulary: token, embedding, Q/K/V,
attention, residual, normalization, MLP, logit, loss, gradient,
fine-tuning memory, generation, and KV persistence.
```

### What this toy model is not

```text
It is not Qwen.
It does not contain a full trained transformer.
It does not have real model-scale weights.
It does not use the GPU or MLX.
It does not prove production language quality.
```

### Completed toy-model steps

```text
Step 8   fine-tuning memory and mitigation strategies
Step 9   connect multiple transformer layers into one forward pass
Step 10  train the toy Q/K/V and attention weights
Step 11  generate several tokens continuously
Step 12  save and restore the toy KV cache
Step 13  advanced attention types, KV layouts, MoE, and memory
```

### Where the real LLM begins

The real model is not created by the toy files. It begins in the MLX
experiments when they load:

```text
mlx-community/Qwen2.5-0.5B-Instruct-4bit
```

The real boundary is:

```text
toy lessons                         real DecaState experiment
------------                         ------------------------
hand-made numbers                   real Qwen model weights
small Python lists                  real tokenizer
CPU teaching math                   MLX/Metal inference
no production cache                 real native K/V cache
                                      DecaState save/restore
```

The toy curriculum explains what the real model does. The MLX experiments
prove DecaState can save and restore state from the real model.

## 17. How does a model choose 24 layers?

### What does “24 layers” mean?

A transformer is a stack of repeated blocks:

```text
token embeddings
      │
      ▼
Layer 1
      │
      ▼
Layer 2
      │
      ▼
   ...
      │
      ▼
Layer 24
      │
      ▼
output head → next token
```

Each layer contains approximately:

```text
Q/K/V attention
      ↓
residual + normalization
      ↓
MLP/feed-forward network
```

The runtime does not decide during inference whether to use 24 or 30 layers.
The model configuration already defines the number of layers, and inference
runs them in order.

### Our real Qwen model

Our tested checkpoint is:

```text
Qwen2.5-0.5B-Instruct-4bit
```

Its published configuration specifies:

```text
24 hidden transformer layers
hidden size: 896
attention heads: 14
key/value heads: 2
```

Source: [Qwen2.5-0.5B-Instruct configuration](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/main/config.json).

```text
24 layers ≠ 24 tokens
24 layers ≠ 24 attention heads
24 layers ≠ 24 weights

24 layers = 24 repeated transformer blocks
```

### Why use more layers?

Use `I like tea` as a simple mental picture:

```text
Layer 1   notices local relationships
Layer 2   improves the combined meaning
Layer 3   connects more context
   ...
Layer 24  produces a rich representation for prediction
```

More layers can provide more transformation capacity, but they also add
sequential computation, latency, memory, training difficulty, and serving
cost. More layers are not automatically better.

```text
MORE LAYERS
    │
    ├── potentially richer transformations
    ├── more capacity for complex patterns
    ├── more sequential processing
    ├── slower inference
    ├── larger KV cache
    ├── harder optimization
    └── higher serving cost
```

### Depth, width, heads, and experts

```text
DEPTH       number of transformer layers
WIDTH       hidden-vector size inside each layer
HEADS       parallel attention subspaces
MLP SIZE    feed-forward capacity inside a layer
EXPERTS     specialist MLPs in a mixture-of-experts model
```

Model designers balance:

```text
quality ↔ latency ↔ memory ↔ training cost ↔ serving cost
```

They train and compare candidate configurations using quality benchmarks,
training curves, scaling experiments, hardware limits, and cost targets.

### Different model families choose different depths

| Model example | Main published depth | Important detail |
|---|---:|---|
| Qwen2.5-0.5B-Instruct | 24 | Dense small model used in our MLX proof |
| DeepSeek-V3 | 61 main hidden layers in the published weight documentation | Also documents a separate MTP module; count configuration fields carefully |
| Kimi-K2-Instruct | 61 | MoE model with 384 routed experts and 8 experts activated per token |

Sources: [DeepSeek-V3 weight structure](https://github.com/deepseek-ai/DeepSeek-V3/blob/main/README_WEIGHTS.md), [Kimi-K2 configuration](https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/config.json).

### Dense versus mixture-of-experts

Dense model:

```text
token → Layer 1 uses its full MLP
      → Layer 2 uses its full MLP
      → Layer 3 uses its full MLP
```

Mixture-of-experts model:

```text
token
  │
  ▼
router chooses useful specialists
  │
  ├── Expert 12
  ├── Expert 87
  └── Expert 201
          │
          ▼
      combine results
```

An MoE model may have many total parameters while activating only some experts
for each token. Experts are not additional sequential transformer layers.

### Why deeper models need more KV-cache memory

Each transformer layer creates its own K/V state:

```text
Layer 1  → K₁/V₁
Layer 2  → K₂/V₂
Layer 3  → K₃/V₃
   ...
Layer 24 → K₂₄/V₂₄
```

The complete cache is therefore:

```text
KV CACHE
├── Layer 1 K/V
├── Layer 2 K/V
├── Layer 3 K/V
├── ...
└── Layer 24 K/V
```

More layers generally mean more K/V tensors to store. DecaState saves and
restores the native state across the model's layers, not just one K/V pair.

### Final rule

```text
The best model is not the one with the most layers.

The best model is the one that gives the required quality
within the training, hardware, latency, memory, and cost budget.
```

## 18. What the 12 steps cover — and what they do not

The 12-step toy curriculum is the **core mechanical path** from text to
attention to generation and KV persistence. It is not yet the complete study
of modern LLMs. We started with a dense transformer because it is the clearest
baseline; MoE is a later variation inside the MLP part of some layers.

### Why dense and MoE were not in the first simple layer

The first layer we studied was:

```text
Q/K/V attention
      ↓
residual + normalization
      ↓
MLP/feed-forward network
```

In that diagram, **MLP means the dense baseline**:

```text
DENSE MLP
every token uses the same MLP weights

hidden vector
      │
      ▼
up/gate projections → activation → down projection
      │
      ▼
updated hidden vector
```

An MoE model changes mainly the MLP part:

```text
MOE MLP
hidden vector
      │
      ▼
router chooses a few experts
      │
      ├── Expert 12: MLP weights
      ├── Expert 87: MLP weights
      └── Expert 201: MLP weights
                 │
                 ▼
           weighted combination
```

The attention path still exists. The difference is that a router selects some
specialist MLPs instead of activating one shared dense MLP for every token.
We postponed this because learning dense attention, residuals, normalization,
and one MLP first makes the MoE extension much easier to understand.

### Complete expert roadmap

```text
FOUNDATION CORE — completed
1. text, tokenizer, token IDs, BOS/UNK
2. embeddings and vectors
3. Q/K/V projections
4. attention scores, scaling, softmax, weighted V
5. residual connections and normalization
6. dense MLP/feed-forward network
7. logits, softmax, sampling, next-token generation
8. loss, teacher forcing, gradients, optimizer updates
9. training memory and fine-tuning choices
10. multiple layers and autoregressive generation
11. KV cache, prefill, decode, save/restore
12. toy state persistence and DecaState boundary
```

```text
ARCHITECTURE DEPTH — next curriculum
13. causal masking: why future tokens are hidden
14. positional information: RoPE and position IDs
15. multi-head, multi-query, and grouped-query attention
16. real dense MLPs: GELU, SiLU, SwiGLU, gate/up/down projections
17. MoE router, experts, top-k routing, load balancing, auxiliary loss
18. model configuration: depth, width, heads, context, parameter budget
```

```text
TRAINING SCIENCE
19. cross-entropy and teacher forcing in full sequences
20. backpropagation through all transformer layers
21. SGD, Adam, AdamW, learning-rate schedules, warmup
22. initialization, normalization, exploding/vanishing gradients
23. pretraining, instruction tuning, preference tuning, RL-style methods
24. data quality, deduplication, contamination, and evaluation splits
```

```text
SYSTEMS AND PERFORMANCE
25. GPU tensors, memory layout, kernels, and batching
26. data, tensor, pipeline, and expert parallelism
27. activation/weight/KV memory accounting
28. quantization: INT8, INT4, FP8 and calibration
29. speculative decoding and multi-token prediction
30. serving, batching, scheduling, rate limits, and observability
```

```text
RELIABILITY AND PRODUCT
31. factuality, hallucination, and grounded generation
32. alignment, safety, prompt injection, and tool security
33. benchmark design, ablations, reproducibility, and statistical gates
34. model routing, caching, portability, and lifecycle management
35. DecaState: native state persistence and state-aware orchestration
```

### What “expert” means in this roadmap

For every component, we should be able to answer five questions:

```text
1. What problem does this component solve?
2. What tensors enter it and what tensors leave it?
3. Which weights or decisions does it use?
4. What does it cost in memory, compute, and latency?
5. How do we test failure, quality, and correctness?
```

The current 12 steps give us the vocabulary and the core forward/inference
mechanics. Step 13 now introduces causal masking, attention layouts, and MoE;
the next lesson is Step 14: positional encoding and RoPE.

---

## 19. Codex Deep Fundamentals — attention, MoE, training, and memory

This section fills in the missing map. The first 12 lessons used a tiny dense
transformer so the arithmetic was easy to see. Real LLMs add different kinds
of attention, different MLP designs, training machinery, and GPU memory
optimizations. These are variations around the same core loop.

### 19.1 The complete transformer block

```text
tokens: “I like tea”
        │
        ▼
embedding + position information
        │
        ▼
┌──────────────────────────────────────────────┐
│ ONE TRANSFORMER LAYER                        │
│                                              │
│  attention: look at useful earlier tokens    │
│       ↓                                      │
│  output projection + residual + normalization│
│       ↓                                      │
│  dense MLP OR MoE router + selected experts  │
│       ↓                                      │
│  residual + normalization                    │
└──────────────────────────────────────────────┘
        │
        ▼
repeat for Layer 2 ... Layer 24 ... final layer
        │
        ▼
logits → probabilities → next token
```

**Attention** mixes information between token positions. **The MLP** changes
each position's representation using learned transformations. **Residuals**
carry the old information forward. **Normalization** keeps numerical scales
stable. **Weights** are the learned numbers that make all of those operations
useful.

### 19.2 “Attention” has two meanings

When people say “attention,” they may mean either:

```text
ATTENTION OPERATION = Q/K/V math inside a layer
ATTENTION TYPE      = the rule deciding which positions may interact
```

Do not confuse the operation with the type of access.

| Type | Plain meaning | `I like tea` picture | Common use |
|---|---|---|---|
| Self-attention | tokens look at tokens in the same sequence | `tea` looks at `I`, `like`, `tea` | almost every transformer |
| Causal self-attention | a token may look only left, never into the future | `like` cannot see future `tea` while predicting it | decoder LLMs |
| Bidirectional self-attention | a token can look left and right | `like` may see both `I` and `tea` | BERT-style encoders |
| Cross-attention | one sequence asks questions about another | answer tokens look at encoded document tokens | encoder-decoder models |
| Local/window attention | look only within a nearby window | `tea` sees the nearest N tokens | long-context efficiency |
| Sparse attention | look at selected positions, not every position | local words plus special summary positions | long-context designs |

The normal chat LLM path is usually **causal self-attention**. The causal
mask is a rule, not an extra learned intelligence:

```text
             MAY LOOK AT
             I   like  tea  next?
I            yes  no    no    no
like         yes  yes   no    no
tea          yes  yes   yes   no
```

The model does not peek at the answer before predicting it.

### 19.3 MHA, GQA, and MQA: three ways to store K/V

The query heads ask questions. Key/value heads hold the searchable context.
The main difference is how many K/V copies are created.

```text
MHA — Multi-Head Attention
32 Q heads → 32 K heads + 32 V heads
every query head has its own K/V head

GQA — Grouped-Query Attention
32 Q heads → 8 K heads + 8 V heads
four Q heads share one K/V head

MQA — Multi-Query Attention
32 Q heads → 1 K head + 1 V head
all Q heads share one K/V pair
```

```text
Same prompt, same layers, same token count:

MHA  ████████████████████  largest K/V cache, most independent K/V detail
GQA  █████                smaller cache, compromise between detail and cost
MQA  ██                   smallest cache, maximum sharing
```

The teaching memory formula is approximately:

```text
K/V bytes ≈ 2 × layers × tokens × KV_heads × head_dimension × bytes_per_value
             ↑                       ↑
             K and V                 not Q heads
```

For the illustrative screenshot example:

```text
layers = 32, tokens = 8,192, head dimension = 128,
bytes/value = 2 (BF16), Q heads = 32

MHA:  KV heads = 32 → about 4 GiB
GQA:  KV heads =  8 → about 1 GiB
MQA:  KV heads =  1 → about 128 MiB
```

These are illustrative full-length K/V-only numbers; real usage also needs
weights, activations, runtime buffers, allocator overhead, and batch space.

### 19.4 One `I like tea` attention calculation

For the last position, pretend the learned projections produced:

```text
Q(tea) = [1, 1]

K(I)    = [1, 0]       V(I)    = [1, 0]
K(like) = [0, 1]       V(like) = [0, 1]
K(tea)  = [1, 1]       V(tea)  = [1, 1]
```

The query asks, “Which earlier representations help me?”

```text
Q × Kᵀ = [1, 1] × ┌─────┬─────┬─────┐
                    │  1  │  0  │  1  │  row 1
                    ├─────┼─────┼─────┤
                    │  0  │  1  │  1  │  row 2
                    └─────┴─────┴─────┘
                       I    like  tea
                = [1, 1, 2]
```

After scaling and softmax:

```text
I       24.8%  ──┐
like    24.8%  ──┼── mix the V vectors
tea     50.4%  ──┘

attention output
= .248[1,0] + .248[0,1] + .504[1,1]
= [0.752, 0.752]
```

The percentages are not human-written labels. They are numbers produced by
the dot products, scaling, softmax, and the current learned weights.

### 19.5 What exactly is a dense MLP?

```text
one token's hidden vector
          │
          ▼
   up/gate projections
          │
          ▼
   GELU / SiLU / SwiGLU
          │
          ▼
   down projection
          │
          ▼
   refined hidden vector
```

Attention lets tokens exchange information. The MLP then processes each token
position separately. In a **dense** model, every token uses the same MLP
weights in that layer:

```text
token 1 ─┐
token 2 ─┼──► the same MLP weights ───► updated vectors
token 3 ─┘
```

“Same weights” does not mean same output: each token enters with a different
vector, so the same function produces different results.

### 19.6 What is MoE and where does the intelligence come from?

MoE means **Mixture of Experts**. It usually replaces the dense MLP in some
layers; it does not remove attention.

```text
token hidden vector
        │
        ▼
small learned ROUTER scores experts
        │
        ├── Expert 4  (selected)
        ├── Expert 19 (selected)
        ├── Expert 80 (not selected)
        └── Expert 121(not selected)
        │
        ▼
weighted selected-expert output
        │
        ▼
residual stream continues
```

The router is a small learned neural function. During training, gradient
signals teach it which experts help which token patterns. During inference,
the router performs ordinary arithmetic; it does not “think” in English or
make a conscious decision.

```text
Dense: each token → one shared MLP
MoE:   each token → router → a few specialist MLPs

MoE can have large TOTAL parameters
while using fewer ACTIVE parameters per token.
```

The trade-off is more model capacity and potentially lower compute per token,
but more complicated routing, memory, communication, balancing, and serving.

### 19.7 Training versus inference

```text
TRAINING (teach the weights)
prompt + known next token
        │
        ▼
forward pass through all layers
        │
        ▼
predicted probabilities vs correct token
        │
        ▼
loss = how wrong was the prediction?
        │
        ▼
backpropagation = assign blame to weights
        │
        ▼
optimizer updates weights a little
```

```text
INFERENCE (use frozen weights)
prompt → forward pass → probabilities → choose next token
                                      │
                                      ▼
                          append token and repeat
```

Backpropagation is not used to answer a normal user question. It is used
during training or fine-tuning to change the model weights. During inference,
the weights stay fixed; only temporary activations and K/V cache grow.

### 19.8 GPU memory: what lives where?

```text
GPU memory during inference
┌──────────────────────────────────────────┐
│ model weights (fixed learned knowledge)  │
│ activations (temporary current compute)  │
│ K/V cache (temporary attention history)  │
│ runtime buffers / batching / allocator   │
└──────────────────────────────────────────┘

GPU memory during training adds:
┌──────────────────────────────────────────┐
│ gradients                                │
│ optimizer state (Adam moments, etc.)     │
│ saved activations for backpropagation     │
└──────────────────────────────────────────┘
```

```text
Inference memory pressure:
  weights + current activations + growing K/V cache

Training memory pressure:
  weights + gradients + optimizer state + activations
```

Activation checkpointing saves fewer intermediate activations and recomputes
some during backpropagation. Sharding splits tensors across GPUs. Offload
moves selected data to CPU or storage. These reduce peak GPU memory but can
increase compute, communication, or latency.

### 19.9 How this connects to DecaState

```text
LOCAL MLX
  model weights loaded locally
  model runtime creates K/V on the GPU
  DecaState saves native K/V state
  new process restores it and avoids old prefill

API PROVIDER
  provider owns model weights and GPU
  provider runtime decides whether its prefix cache hits
  DecaState can prepare stable prefixes, route, and measure usage
  DecaState cannot directly read or save Anthropic/OpenAI server K/V
```

The safe product boundary is therefore:

```text
local: direct native state control
API:   cache-aware orchestration + transparent measurement
```

### 19.10 The expert checklist for every new concept

```text
1. What problem does it solve?
2. Is it a learned weight, a runtime rule, or temporary state?
3. What enters and leaves it?
4. Does it affect quality, compute, memory, latency, or cost?
5. Is it used in training, inference, or both?
6. How would we test the claim?
```

Throughout Steps 13–17, keep asking what happens to the three tokens in
`I like tea`: attention type controls who may look at whom;
MHA/GQA/MQA controls how K/V are shared; dense/MoE controls how the MLP
capacity is used; backpropagation teaches the weights; inference uses those
fixed weights to create temporary K/V and produce tokens.
