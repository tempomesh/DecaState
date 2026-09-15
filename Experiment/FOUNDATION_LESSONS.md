# Foundation Experiments: Learn Without the Conversation

These files are deliberately tiny teaching machines. They do not implement a
full Qwen model, do not train a useful LLM, and do not use MLX, Ollama, an API,
or the GPU. Their job is to make one idea visible at a time.

Run them in order:

```bash
cd /Users/ashish/DECASTATE
source .venv/bin/activate
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

## The whole learning path

```text
01 text
   ↓ tokenizer → token IDs → embedding vectors
02 embeddings
   ↓ WQ/WK/WV → Q/K/V
03 Q/K/V
   ↓ scores → scale → softmax → weighted V
04 attention output
   ↓ residual → normalization → MLP → residual → normalization
05 layer output
   ↓ output weights → logits → probabilities → next token
```

## 01 — `experiments/08_step1_tokens_embeddings.py`

### What problem does it teach?

The neural network does not receive the English sentence directly. It first
needs numbers.

```text
"I like tea"
      ↓ tokenizer
[BOS, I, like, tea]
      ↓ vocabulary lookup
[0, 1, 2, 3]
      ↓ embedding lookup
vectors of numbers
```

### What the code does

1. Defines a tiny vocabulary.
2. Assigns each token a simple ID.
3. Assigns each ID a small four-number embedding.
4. Prints the sequence that will enter the first transformer layer.
5. Checks that the result is deterministic.

### What the output means

```text
position  token  ID  embedding
0         BOS    0   [0.0, 0.0, 0.0, 1.0]
1         I      1   [1.0, 0.0, 0.0, 0.1]
```

The embedding is not a definition in English. It is a small teaching vector.
In a real model, the embedding has many more dimensions and is learned during
training.

### What it does not teach yet

```text
No Q/K/V
No attention
No GPU
No answer generation
```

The output becomes the input for Step 2.

## 02 — `Experiment/02_embeddings_qkv.py`

### What problem does it teach?

How an embedding becomes three different views of the same token:

```text
Q = what the current token is looking for
K = what each token offers for matching
V = information carried by each token
```

### What the code does

1. Creates three tiny embeddings for `I`, `like`, and `tea`.
2. Defines small teaching matrices `WQ`, `WK`, and `WV`.
3. Multiplies each embedding by those matrices.
4. Prints Q, K, and V for every token.
5. Shows that `tea` can create a query and compare it with earlier keys.

### Common-language picture

```text
embedding
   │
   ├── WQ → question
   ├── WK → label for matching
   └── WV → useful information
```

### Important detail

`WQ`, `WK`, and `WV` are model weights. In this file they are hand-chosen so
the numbers are easy to understand. In a real model, training learns them.

### Connection to the KV cache

```text
old token processed
      ↓
save its K and V
      ↓
new token creates Q
      ↓
Q reads old K/V during attention
```

## 03 — `Experiment/03_attention.py`

### What problem does it teach?

How attention decides which tokens matter and turns those decisions into one
context vector.

### What the code does

1. Defines one query: `Q = [1, 1]`.
2. Defines three key vectors as columns, one for each token.
3. Calculates all dot products at once:

```text
Q × K = [1, 1, 2]
```

4. Divides by `√d_k` to keep scores stable.
5. Applies softmax so the scores become percentages.
6. Uses those percentages to mix the Value vectors.
7. Prints and verifies the final attention output.

### The calculation in plain language

```text
compare tea with I, like, tea
      ↓
get raw scores
      ↓
turn scores into percentages
      ↓
take that percentage of each V
      ↓
add the pieces together
```

### The matrix shape lesson

```text
Q:     1 × 2
K:     2 × 3
Q × K: 1 × 3
V:     3 × 2
output:1 × 2
```

The three output scores correspond to:

```text
I, like, tea
```

### Why the test matters

The script checks that the scores, attention weights, and output remain
deterministic. This is a math lesson, not a claim that these tiny numbers are
the actual Qwen values.

## 04 — `Experiment/04_transformer_layer.py`

### What problem does it teach?

Attention is not the whole transformer layer. After attention, the layer keeps
the old signal, stabilizes the numbers, transforms the result, and sends it to
the next layer.

```text
attention output
      ↓
residual connection
      ↓
normalization
      ↓
MLP
      ↓
residual connection
      ↓
normalization
      ↓
next layer
```

### What the code does

It starts with:

```text
input x          = [1.0, 2.0]
attention output = [0.75, 0.75]
```

Then it performs:

```text
1. x + attention             → [1.75, 2.75]
2. Layer normalization        → [-1.0, 1.0]
3. MLP matrix + ReLU          → [0.0, 1.0]
4. normalized + MLP           → [-1.0, 2.0]
5. second normalization       → [-1.0, 1.0]
```

### Common-language meaning

```text
Residual      = do not throw away the original information
Normalization = keep the numbers healthy and stable
MLP           = process/refine the gathered meaning
```

### Important realism note

This is a simplified post-norm-style teaching block using ReLU. Real Qwen
implementations use much larger vectors, learned normalization parameters,
pre-normalization, and a model-specific activation such as SwiGLU. The roles
are the same even though the exact implementation differs.

## 05 — `Experiment/05_logits_next_token.py`

### What problem does it teach?

How the final hidden vector becomes a choice among vocabulary tokens.

```text
layer output
     ↓
output weights
     ↓
logits: raw preference scores
     ↓
softmax
     ↓
probabilities
     ↓
select next token
```

### What the code does

1. Starts with the Step 4 layer output `[-1.0, 1.0]`.
2. Defines one small output-weight vector per vocabulary token.
3. Calculates a dot product for each possible token.
4. Calls those raw scores logits.
5. Applies softmax so they become probabilities.
6. Selects the highest-probability token.
7. Verifies that the probabilities sum to one.

### What logits mean

Logits are not percentages yet:

```text
logit = model's raw preference before softmax
```

Softmax turns them into a distribution:

```text
"I"      → 16.96%
"like"   → 20.71%
"tea"    → 20.71%
"coffee" → 18.74%
"."      → 22.89%
```

The vocabulary in this file is tiny and the weights are hand-chosen. It is
showing the mechanism, not producing fluent language.

## 06 — `Experiment/06_training_loss_backprop.py`

### What problem does it teach?

The first five scripts used weights that a human typed in. A real model must
learn better weights from examples. Step 6 shows that learning loop:

```text
prediction
    ↓ compare with the correct answer
loss: how wrong was the prediction?
    ↓
gradient: which direction should each score move?
    ↓
update weights
    ↓
try the same example again
```

### What the code does

1. Starts with a tiny hidden vector and three possible output tokens.
2. Uses output weights to calculate logits.
3. Converts logits into probabilities with softmax.
4. Treats `tea` as the correct answer.
5. Calculates cross-entropy loss.
6. Calculates the gradient for each output score.
7. Updates the weights with gradient descent.
8. Repeats the loop and verifies that loss decreases.

### Training versus inference

```text
TRAINING                         INFERENCE
examples + correct answers       user prompt
          ↓                              ↓
change model weights             use fixed learned weights
          ↓                              ↓
save the improved model          generate an answer
```

DecaState's KV cache belongs mainly to the inference side. It stores temporary
attention state for a running prompt; it is not the same thing as the learned
model weights and it does not perform backpropagation.

## What these files collectively prove

```text
They prove the mechanics are understandable and deterministic.
They do not prove that a useful LLM can be trained from these five files.
They do not replace Qwen or the MLX runtime.
```

The next natural lessons are:

```text
06 loss and backpropagation                         PASS (make step6)
07 train tiny model, freeze it, then run inference   (make step7)
08 fine-tuning memory and mitigation strategies     (make step8)
09 connect multiple transformer layers                   (make step9)
10 train toy Q/K/V and attention weights                 (make step10)
11 generate several tokens continuously                  (make step11)
12 toy K/V state creation and restore                    (make step12)
```
