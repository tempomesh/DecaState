"""STEP 8 LESSON — fine-tuning memory, explained with small calculations.

This lesson connects Step 6/7 training to the Google interview question:
"Why does fine-tuning run out of GPU memory, and how do we make it fit?"

It has two parts:

    1. a tiny forward -> loss -> gradient update, just like Step 6;
    2. a memory estimator showing what full fine-tuning, LoRA, QLoRA,
       activation checkpointing, sharding, and offload change.

The memory numbers are planning estimates, not a measurement of a real GPU
allocator. A real run must be profiled because frameworks add kernels,
fragmentation, communication buffers, and implementation-specific state.
"""
from __future__ import annotations

import math


# -----------------------------
# Part 1: tiny training example
# -----------------------------

HIDDEN = [-1.0, 1.0]
VOCAB = ["I", "like", "tea"]
TARGET_INDEX = 2
TINY_WEIGHTS = [
    [0.20, 0.10],
    [0.10, 0.20],
    [-0.05, -0.05],
]


def softmax(scores: list[float]) -> list[float]:
    """Turn raw token scores into probabilities."""
    peak = max(scores)
    exponentials = [math.exp(score - peak) for score in scores]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def tiny_training_step(weights: list[list[float]]) -> tuple[float, float]:
    """Run one teaching update and return (loss_before, loss_after).

    This is the same idea as Step 6: calculate a prediction, compare it with
    the known correct token, calculate the gradient, and adjust weights.
    """
    logits = [
        sum(feature * weight for feature, weight in zip(HIDDEN, row))
        for row in weights
    ]
    probabilities = softmax(logits)
    loss_before = -math.log(probabilities[TARGET_INDEX])

    # For softmax + cross-entropy, gradient = prediction - one-hot target.
    score_gradients = probabilities.copy()
    score_gradients[TARGET_INDEX] -= 1.0
    learning_rate = 0.40
    for row_index, gradient in enumerate(score_gradients):
        for feature_index, feature in enumerate(HIDDEN):
            weights[row_index][feature_index] -= learning_rate * gradient * feature

    new_logits = [
        sum(feature * weight for feature, weight in zip(HIDDEN, row))
        for row in weights
    ]
    new_probabilities = softmax(new_logits)
    loss_after = -math.log(new_probabilities[TARGET_INDEX])
    return loss_before, loss_after


# ----------------------------------
# Part 2: transparent memory estimate
# ----------------------------------

PARAMETERS = 7_000_000_000
LAYERS = 32
MICRO_BATCH = 1
SEQUENCE_LENGTH = 2048
HIDDEN_SIZE = 4096
ACTIVATION_FACTOR = 4  # teaching estimate for saved intermediate values
GPU_COUNT = 4


def gibibytes(byte_count: float) -> float:
    """Convert bytes to GiB for easier reading."""
    return byte_count / (1024**3)


def memory_estimate(
    *,
    parameter_bytes: float,
    trainable_fraction: float,
    checkpointing: bool = False,
    shard_count: int = 1,
    offload: bool = False,
) -> dict[str, float]:
    """Estimate major memory buckets for one illustrative configuration.

    The assumed full-Adam layout is:

        parameter + gradient + FP32 master + Adam m + Adam v
        2 + 2 + 4 + 4 + 4 = 16 bytes per trainable parameter

    For LoRA/QLoRA only the adapter fraction is trainable, so optimizer and
    gradient state are charged to that smaller fraction. The frozen base still
    occupies weight storage, possibly quantized.
    """
    trainable_parameters = PARAMETERS * trainable_fraction
    base_weights = PARAMETERS * parameter_bytes
    trainable_state = trainable_parameters * 16.0
    activation_bytes = (
        MICRO_BATCH
        * SEQUENCE_LENGTH
        * HIDDEN_SIZE
        * LAYERS
        * ACTIVATION_FACTOR
        * 2  # BF16/FP16-like activation estimate
    )
    if checkpointing:
        activation_bytes *= 0.40

    divisor = max(shard_count, 1)
    gpu_base = base_weights / divisor
    gpu_trainable_state = trainable_state / divisor
    gpu_activations = activation_bytes

    # Offload means the base weights are not counted as resident GPU memory in
    # this simplified picture. Real systems still need staging buffers.
    if offload:
        gpu_base *= 0.10

    return {
        "base_weights_gib": gibibytes(gpu_base),
        "trainable_state_gib": gibibytes(gpu_trainable_state),
        "activations_gib": gibibytes(gpu_activations),
        "total_gib": gibibytes(gpu_base + gpu_trainable_state + gpu_activations),
    }


def show_estimate(name: str, estimate: dict[str, float]) -> None:
    """Print one strategy in a consistent, readable form."""
    print(f"{name}")
    print(f"  base weights:    {estimate['base_weights_gib']:>7.1f} GiB")
    print(f"  trainable state: {estimate['trainable_state_gib']:>7.1f} GiB")
    print(f"  activations:     {estimate['activations_gib']:>7.1f} GiB")
    print(f"  estimated total: {estimate['total_gib']:>7.1f} GiB")


def main() -> None:
    print("STEP 8 · FINE-TUNING MEMORY")
    print("=" * 58)
    print("PART 1 · THE LEARNING LOOP")
    print("  “I like tea” → forward pass → loss → gradients → new weights")
    weights = [row.copy() for row in TINY_WEIGHTS]
    before, after = tiny_training_step(weights)
    print(f"  loss before update: {before:.4f}")
    print(f"  loss after update:  {after:.4f}")
    print()
    print("PART 2 · WHERE GPU MEMORY GOES")
    print("  weights + gradients + optimizer + activations + temporary buffers")
    print()
    print("ASCII MEMORY MAP")
    print("  model weights       = permanent learned recipe")
    print("  gradients           = correction for each trainable weight")
    print("  Adam state           = optimizer memory (m and v)")
    print("  activations          = saved layer outputs for backpropagation")
    print("  temporary workspace  = attention kernels and communication")
    print()
    print("ILLUSTRATIVE CONFIGURATION")
    print(f"  model: {PARAMETERS / 1e9:.0f}B parameters, {LAYERS} layers")
    print(f"  sequence: {SEQUENCE_LENGTH} tokens, micro-batch: {MICRO_BATCH}")
    print(f"  assumption: {PARAMETERS / 1e9:.0f}B × 16 bytes ≈ {gibibytes(PARAMETERS * 16):.1f} GiB persistent full-Adam state")
    print("  Note: this is an estimate, not a GPU profiler result.")
    print()

    full = memory_estimate(parameter_bytes=2, trainable_fraction=1.0)
    lora = memory_estimate(parameter_bytes=2, trainable_fraction=0.001)
    qlora = memory_estimate(parameter_bytes=0.5, trainable_fraction=0.001)
    checkpointed = memory_estimate(parameter_bytes=2, trainable_fraction=1.0, checkpointing=True)
    sharded = memory_estimate(parameter_bytes=2, trainable_fraction=1.0, shard_count=GPU_COUNT)
    offloaded = memory_estimate(parameter_bytes=2, trainable_fraction=1.0, offload=True)

    show_estimate("FULL FINE-TUNING · all weights trainable", full)
    show_estimate("LoRA · frozen base + 0.1% trainable adapter", lora)
    show_estimate("QLoRA · quantized base + 0.1% adapter", qlora)
    show_estimate("ACTIVATION CHECKPOINTING · recompute some activations", checkpointed)
    show_estimate(f"SHARDING · split across {GPU_COUNT} GPUs", sharded)
    show_estimate("OFFLOAD · move most base weights away from GPU", offloaded)

    print()
    print("HOW TO CHOOSE")
    print("  Need every weight to change?        full fine-tuning")
    print("  Need lower memory, similar base?    LoRA/QLoRA")
    print("  Activations are the problem?        checkpointing")
    print("  Several GPUs are available?         sharding")
    print("  GPU memory is still insufficient?   offload or smaller model")
    print()
    print("NOT YET")
    print("  This script does not allocate 7B parameters or use a GPU.")
    print("  It teaches the accounting and the trade-offs.")
    print("  Real training still needs a profiler and a quality evaluation.")

    assert after < before
    assert full["total_gib"] > lora["total_gib"]
    assert qlora["base_weights_gib"] < lora["base_weights_gib"]
    assert checkpointed["activations_gib"] < full["activations_gib"]
    assert sharded["base_weights_gib"] < full["base_weights_gib"]
    print("\nTEST PASS: training, memory buckets, and mitigation estimates are consistent.")


if __name__ == "__main__":
    main()
