# Tiny Transformer Curriculum

This directory is the beginner-friendly laboratory for understanding how an
LLM works, one operation at a time. It uses the project's existing `.venv` and
does not download a model or use Ollama, MLX, an API key, or the GPU.

## Run the first lesson

```bash
cd /Users/ashish/DECASTATE/Experiment
../.venv/bin/python 01_tokens_embeddings.py
```

Or from the project root:

```bash
cd /Users/ashish/DECASTATE
source .venv/bin/activate
make step1
```

For a self-contained explanation of every Python file, read
[`FOUNDATION_LESSONS.md`](FOUNDATION_LESSONS.md) before or while running the
commands.

## Learning sequence

```text
01  text → tokenizer → token IDs → embeddings          PASS
02  embeddings → one transformer layer → Q/K/V         PASS (make step2)
03  Q × Kᵀ → softmax → weighted V (attention)    PASS (make step3)
04  attention → residual + layer norm + MLP          PASS (make step4)
05  layer output → logits → next-token probabilities  PASS (make step5)
06  loss → backpropagation → learned weights          (make step6)
07  train tiny model → freeze → inference             (make step7)
08  fine-tuning memory: loss + GPU memory trade-offs  (make step8)
09  connect multiple transformer layers                   (make step9)
10  train toy Q/K/V and attention weights                 (make step10)
11  generate several tokens continuously                  (make step11)
12  toy KV cache → save → process death → restore        (make step12)
```

The existing DecaState production demonstrations remain in `../experiments/`.
This directory is specifically for transparent, small, educational models.
