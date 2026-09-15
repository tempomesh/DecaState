"""STEP 4 LESSON — one complete transformer layer.

Attention is only one part of a layer. This teaching block performs:

    attention -> residual add -> normalization -> MLP
              -> residual add -> normalization -> next layer

Attention means "look around". The MLP means "process what you found".
Residuals keep the original signal available; normalization keeps numbers
well-behaved. The vectors and weights are tiny and hand-made so every step is
visible. Real Qwen layers use different dimensions, ordering, and activations.
"""
from __future__ import annotations

import math


# Input representation for the current token. Real hidden vectors are much
# larger. This attention output comes from the Step 3 teaching calculation.
INPUT = [1.0, 2.0]
ATTENTION_OUTPUT = [0.75, 0.75]
# Tiny MLP weights. Real MLPs expand the vector, apply GELU/SiLU, then project
# it back down. We use a two-number ReLU version to keep the lesson visible.
W_MLP = [[2.0, 0.0], [1.0, 1.0]]


def layer_norm(vector: list[float]) -> tuple[list[float], float, float, float]:
    """Center and scale a vector so later calculations stay stable."""
    mean = sum(vector) / len(vector)
    variance = sum((value - mean) ** 2 for value in vector) / len(vector)
    std = math.sqrt(variance)
    normalized = [(value - mean) / std for value in vector]
    return normalized, mean, variance, std


def matvec(vector: list[float], matrix: list[list[float]]) -> list[float]:
    """Apply the MLP's small linear transformation."""
    return [
        sum(vector[row] * matrix[row][column] for row in range(len(vector)))
        for column in range(len(matrix[0]))
    ]


def main() -> None:
    # Keep the original signal and add the new context to it.
    residual_1 = [a + b for a, b in zip(INPUT, ATTENTION_OUTPUT)]
    # Put the combined numbers into a predictable range.
    norm_1, mean_1, variance_1, std_1 = layer_norm(residual_1)
    # The MLP refines this token's features independently; attention mixed
    # information between tokens, while the MLP processes this vector.
    linear = matvec(norm_1, W_MLP)
    # ReLU keeps positive signals and removes negative ones. It is chosen for
    # teaching; Qwen uses a different activation.
    mlp = [max(0.0, value) for value in linear]
    # Add the MLP refinement without throwing away the earlier representation.
    residual_2 = [a + b for a, b in zip(norm_1, mlp)]
    # This final normalized vector is passed to Layer 2.
    output, mean_2, variance_2, std_2 = layer_norm(residual_2)

    print("STEP 4 · ONE TRANSFORMER LAYER")
    print("=" * 48)
    print("INPUT x(tea):          ", INPUT)
    print("ATTENTION OUTPUT a:    ", ATTENTION_OUTPUT)
    print()
    print("1. RESIDUAL 1: x + a:  ", residual_1)
    print(f"2. NORM 1: mean={mean_1:.2f}, variance={variance_1:.2f}, std={std_1:.2f}")
    print("   normalized:          ", norm_1)
    print("3. MLP linear:          ", linear)
    print("   ReLU MLP output:     ", mlp)
    print("4. RESIDUAL 2:           ", residual_2)
    print(f"5. NORM 2: mean={mean_2:.2f}, variance={variance_2:.2f}, std={std_2:.2f}")
    print("   LAYER 1 OUTPUT:       ", output)
    print("   next:                 Layer 2 input")
    print()
    print("ASCII FLOW")
    print("attention output → residual → normalize → MLP")
    print("       → residual → normalize → next layer")
    print()
    print("TEST PASS: Step 4 transformer-layer calculation is deterministic.")

    assert residual_1 == [1.75, 2.75]
    assert norm_1 == [-1.0, 1.0]
    assert linear == [-1.0, 1.0]
    assert mlp == [0.0, 1.0]
    assert residual_2 == [-1.0, 2.0]
    assert output == [-1.0, 1.0]


if __name__ == "__main__":
    main()
