"""Step 13 — advanced transformer fundamentals in one small, runnable lesson.

This is still a teaching model, not Qwen.  It connects the ideas in section 19
of 01_foundations.md/html with visible numbers:

1. causal attention masking;
2. MHA, GQA, and MQA KV-cache memory;
3. dense MLP versus a tiny MoE router; and
4. training memory versus inference memory.

Run from the repository root with: make step13
"""

from math import ceil


def causal_mask(tokens):
    """Show which earlier positions each token is allowed to read."""
    print("\n1) CAUSAL ATTENTION MASK")
    print("A token can look left, but not into the future.")
    for row, token in enumerate(tokens):
        allowed = ["YES" if col <= row else "NO" for col in range(len(tokens))]
        print(f"{token:>5} -> " + "  ".join(allowed))
    print("      " + "  ".join(f"{t:>3}" for t in tokens))


def kv_cache_bytes(layers, tokens, kv_heads, head_dim, bytes_per_value):
    """Approximate K+V bytes: 2 tensors times all dimensions."""
    return 2 * layers * tokens * kv_heads * head_dim * bytes_per_value


def gibibytes(value):
    return value / (1024**3)


def compare_kv_layouts():
    """Show why sharing K/V heads reduces cache memory."""
    print("\n2) MHA vs GQA vs MQA KV CACHE")
    layers, tokens, q_heads, head_dim, value_bytes = 32, 8192, 32, 128, 2
    layouts = [("MHA", q_heads), ("GQA", 8), ("MQA", 1)]
    print("Illustration: 32 layers, 8,192 tokens, 128-dim head, BF16 (2 bytes).")
    for name, kv_heads in layouts:
        size = kv_cache_bytes(layers, tokens, kv_heads, head_dim, value_bytes)
        print(f"{name}: Q heads={q_heads:>2}, KV heads={kv_heads:>2}, "
              f"K+V cache≈{gibibytes(size):.3f} GiB")
    print("Formula: 2 × layers × tokens × KV_heads × head_dim × bytes/value")
    print("The 2 counts K and V. GQA/MQA share K/V; they do not remove Q heads.")


def softmax(values):
    """Tiny stable softmax for the router demonstration."""
    largest = max(values)
    exps = [pow(2.718281828, value - largest) for value in values]
    total = sum(exps)
    return [value / total for value in exps]


def demonstrate_moe():
    """Show that a learned router selects experts inside the MLP area."""
    print("\n3) DENSE MLP vs MoE")
    print("Dense: every token -> the same MLP weights")
    print("MoE:   every token -> router -> a few specialist MLPs")
    expert_names = ["code", "language", "numbers", "planning"]
    router_scores = [2.2, 0.4, 1.7, 0.1]
    probabilities = softmax(router_scores)
    ranked = sorted(zip(probabilities, expert_names), reverse=True)
    print("Router scores:", ", ".join(f"{name}={score:.2f}" for name, score in zip(expert_names, router_scores)))
    print("Router probabilities:", ", ".join(f"{name}={prob:.1%}" for prob, name in ranked))
    selected = ranked[:2]
    print("Top-2 experts used for this token:", ", ".join(name for _, name in selected))
    print("The router is learned during training; inference only performs this arithmetic.")


def memory_buckets():
    """Contrast what must be retained during training and inference."""
    print("\n4) TRAINING vs INFERENCE MEMORY")
    print("Training:   weights + gradients + optimizer state + saved activations")
    print("Inference:  weights + temporary activations + growing K/V + buffers")
    print("Activation checkpointing: save fewer activations, recompute some later.")
    print("Sharding: split tensors across devices. Offload: move selected data to CPU.")


def main():
    tokens = ["I", "like", "tea", "?"]
    print("STEP 13 — ADVANCED FUNDAMENTALS")
    print("These demonstrations explain section 19; they do not train Qwen.")
    causal_mask(tokens)
    compare_kv_layouts()
    demonstrate_moe()
    memory_buckets()
    print("\nSTEP 13 COMPLETE")
    print("Attention type controls access; MHA/GQA/MQA controls K/V sharing;")
    print("MoE controls which MLP experts run; training changes weights; inference uses them.")


if __name__ == "__main__":
    main()
