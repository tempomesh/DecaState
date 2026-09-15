"""STEP 3 LESSON — attention decides what matters right now.

The current token has a Query. Every token has a Key and a Value. Attention:

    1. compares Q with every K;
    2. scales the scores so the numbers stay stable;
    3. uses softmax to turn scores into percentages;
    4. uses those percentages to mix the V vectors.

For ``I like tea`` this creates one contextual vector. It is a transparent
toy calculation, not the real Qwen values.
"""
from __future__ import annotations

import math


# Query for the current token (tea). It has two features in this toy model.
Q = [1.0, 1.0]  # shape: 1 x 2
# One key for I, one for like, and one for tea. Conceptually K is 2 x 3.
K_COLUMNS = [
    [1.0, 0.0],  # I
    [0.0, 1.0],  # like
    [1.0, 1.0],  # tea
]
V_ROWS = [
    [1.0, 0.0],  # V(I)
    [0.0, 1.0],  # V(like)
    [1.0, 1.0],  # V(tea)
]
TOKENS = ["I", "like", "tea"]


def dot(left: list[float], right: list[float]) -> float:
    """Calculate one Q·K similarity score."""
    return sum(a * b for a, b in zip(left, right))


def softmax(values: list[float]) -> list[float]:
    """Turn scores into positive percentages that add up to one."""
    exponentials = [math.exp(value) for value in values]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def main() -> None:
    # 1. Compare the current query with every key.
    raw_scores = [dot(Q, key) for key in K_COLUMNS]
    # 2. Scale for numerical stability.
    scale = math.sqrt(len(Q))
    scaled_scores = [score / scale for score in raw_scores]
    # 3. The runtime converts the scores into attention percentages.
    attention_weights = softmax(scaled_scores)
    # 4. Those percentages decide how much of each Value is mixed into the
    # current token's new context vector.
    output = [
        sum(weight * row[column] for weight, row in zip(attention_weights, V_ROWS))
        for column in range(len(V_ROWS[0]))
    ]

    print("STEP 3 · ATTENTION: Q × K → SCALE → SOFTMAX → V")
    print("=" * 56)
    print("Q = [1  1]                         shape: 1 × 2")
    print("K = [1  0  1]                     shape: 2 × 3")
    print("    [0  1  1]")
    print("V = [1  0]                         shape: 3 × 2")
    print("    [0  1]")
    print("    [1  1]")
    print()
    print("Raw scores Q × K:")
    for token, score in zip(TOKENS, raw_scores):
        print(f"  Q · K({token:4}) = {score:.3f}")
    print(f"raw scores    = {[round(value, 3) for value in raw_scores]}")
    print(f"sqrt(d_k)     = {scale:.3f}")
    print(f"scaled scores = {[round(value, 3) for value in scaled_scores]}")
    print()
    print("Softmax attention percentages:")
    for token, weight in zip(TOKENS, attention_weights):
        print(f"  {token:4} → {weight:.3%}")
    print()
    print("Weighted Value mixer:")
    for token, weight, value in zip(TOKENS, attention_weights, V_ROWS):
        weighted = [weight * item for item in value]
        print(f"  {weight:.3f} × V({token:4}) {value} = {[round(item, 3) for item in weighted]}")
    print(f"ATTENTION OUTPUT = {[round(value, 3) for value in output]}")
    print()
    print("ASCII FLOW")
    print("  Q × K → raw scores → divide by sqrt(d_k) → softmax")
    print("       → attention percentages → percentages × V → output")
    print()
    print("TEST PASS: Step 3 attention calculation is deterministic.")

    assert raw_scores == [1.0, 1.0, 2.0]
    assert abs(sum(attention_weights) - 1.0) < 1e-12
    assert all(abs(actual - expected) < 1e-3 for actual, expected in zip(output, [0.752, 0.752]))


if __name__ == "__main__":
    main()
