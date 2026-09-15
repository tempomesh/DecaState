"""Step 15 — MHA, GQA, and MQA with visible KV-cache arithmetic.

Run with: make step15. They all use Q/K/V attention; they differ in how many
K/V heads are stored and shared during generation.
"""


def cache_bytes(layers, tokens, kv_heads, head_dim, bytes_per_value):
    return 2 * layers * tokens * kv_heads * head_dim * bytes_per_value


def main():
    layers, tokens, q_heads, head_dim, value_bytes = 32, 8192, 32, 128, 2
    print("STEP 15 — MHA vs GQA vs MQA")
    print("Running example: for `I like tea`, each token creates Q/K/V in every layer.")
    print("The K/V for I and like stay available when tea asks its attention question.")
    print("Q heads ask questions. K/V heads store reusable context.")
    print("MHA: 32 Q -> 32 K/V heads; every Q head has its own K/V")
    print("GQA: 32 Q ->  8 K/V heads; groups of Q heads share K/V")
    print("MQA: 32 Q ->  1 K/V head; all Q heads share K/V")
    print("\nIllustration: 32 layers × 8,192 tokens × 128 dimensions × BF16")
    for name, kv_heads in [("MHA", 32), ("GQA", 8), ("MQA", 1)]:
        gib = cache_bytes(layers, tokens, kv_heads, head_dim, value_bytes) / 1024**3
        print(f"{name}: Q heads={q_heads}, KV heads={kv_heads}, K+V≈{gib:.3f} GiB")
    print("Formula: 2 × layers × tokens × KV_heads × head_dimension × bytes/value")
    print("K/V-only memory; weights, activations, buffers, and batching add more.")
    print("STEP 15 COMPLETE")


if __name__ == "__main__":
    main()
