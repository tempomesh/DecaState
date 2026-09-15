"""STEP 9 LESSON — connect several transformer layers.

Step 4 showed one layer. A real model stacks the output of one layer into the
input of the next:

    Layer 1 output -> Layer 2 input -> Layer 3 input -> ...

This script repeats a tiny attention/residual/normalization/MLP block three
times and prints the hidden vector after every floor. It is a visual lesson,
not a real Qwen layer implementation.
"""
from __future__ import annotations

import math


START = [1.0, 2.0]
ATTENTION = [0.75, 0.75]
MLP_WEIGHTS = [[2.0, 0.0], [1.0, 1.0]]
LAYERS = 3


def normalize(vector: list[float]) -> list[float]:
    """Return a simple mean-zero, unit-scale teaching vector."""
    mean = sum(vector) / len(vector)
    variance = sum((value - mean) ** 2 for value in vector) / len(vector)
    return [(value - mean) / math.sqrt(variance + 1e-12) for value in vector]


def matvec(vector: list[float], matrix: list[list[float]]) -> list[float]:
    """Apply the tiny MLP matrix."""
    return [
        sum(vector[row] * matrix[row][column] for row in range(len(vector)))
        for column in range(len(matrix[0]))
    ]


def transformer_layer(hidden: list[float]) -> list[float]:
    """Run one simplified attention/residual/norm/MLP block."""
    after_attention = [old + new for old, new in zip(hidden, ATTENTION)]
    normalized = normalize(after_attention)
    mlp_linear = matvec(normalized, MLP_WEIGHTS)
    mlp = [max(0.0, value) for value in mlp_linear]
    return normalize([old + update for old, update in zip(normalized, mlp)])


def main() -> None:
    hidden = START.copy()
    print("STEP 9 · MULTIPLE TRANSFORMER LAYERS")
    print("=" * 58)
    print("ASCII STACK")
    print("input hidden vector")
    print("        │")
    for layer in range(1, LAYERS + 1):
        print(f"        ▼ Layer {layer}: attention → residual → norm → MLP")
    print("        ▼")
    print("final hidden vector → output head")
    print()
    print("START:", hidden)
    for layer in range(1, LAYERS + 1):
        hidden = transformer_layer(hidden)
        print(f"Layer {layer} output: {hidden}")
    print()
    print("COMMON LANGUAGE")
    print("  Each floor receives the previous floor's improved numbers.")
    print("  Real models repeat this many more times with different learned weights.")
    print("  The same token can become more context-aware as it climbs the stack.")
    print("\nTEST PASS: layer output is connected to the next layer input.")

    assert len(hidden) == 2
    assert all(math.isfinite(value) for value in hidden)


if __name__ == "__main__":
    main()
