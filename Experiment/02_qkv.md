# Step 2: Embeddings → Q/K/V

This is the first transformer-layer lesson. It uses small hand-written numbers
so every calculation is visible. It is not a trained model and does not use
MLX, Ollama, an API, or the GPU.

Run it from the project root:

```bash
cd /Users/ashish/DECASTATE
make step2
```

The flow is:

```text
token
  ↓
embedding vector
  ↓ multiply by learned matrices WQ, WK, WV
Q / K / V
```

```text
Q = what the current token is looking for
K = what each earlier token says it contains
V = information carried by each token
```

For the current token `tea`:

```text
Q(tea) compares with K(I), K(like), K(tea)
          ↓
attention scores
          ↓
attention weights
          ↓
weighted mixture of V vectors
```

The KV-cache connection is:

```text
Process old tokens:  I       like
                    │         │
                    └─ save K and V ─┐
                                      ▼
New token:              tea → create Q(tea)
                              read old K/V
                              calculate attention
                              append K(tea), V(tea)
```

In a real model, the vectors are much larger and every transformer layer has
its own K/V arrays. The rule is the same: the model runtime calculates Q/K/V;
DecaState can later preserve the resulting native state.
