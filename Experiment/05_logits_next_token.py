"""STEP 5 LESSON — turn the final vector into the next-token choice.

The transformer has produced a hidden vector: a numeric representation of the
context. The output head compares it with one weight vector per candidate
token. Each dot product is a *logit*.

    hidden vector -> logits -> softmax percentages -> next token

The weights here are hand-picked, so the result is repeatable and readable. A
real model has a huge vocabulary, trained output weights, and may sample
instead of always choosing the largest probability.
"""
from __future__ import annotations

import math


# Output from our tiny Step 4 teaching layer.
HIDDEN = [-1.0, 1.0]
VOCAB = ["I", "like", "tea", "coffee", "."]
# One small output vector for each candidate token. Real vectors are enormous.
OUTPUT_WEIGHTS = {
    "I": [0.2, 0.1],
    "like": [0.1, 0.2],
    "tea": [-0.2, -0.1],
    "coffee": [0.5, 0.5],
    ".": [-0.8, -0.6],
}


def softmax(values: list[float]) -> list[float]:
    """Convert logits into probabilities that add up to 100 percent."""
    peak = max(values)
    exponentials = [math.exp(value - peak) for value in values]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def main() -> None:
    # A logit asks: "How compatible is this possible next token with the
    # hidden context?" The model has not selected a token yet.
    logits = {
        token: sum(hidden * weight for hidden, weight in zip(HIDDEN, weights))
        for token, weights in OUTPUT_WEIGHTS.items()
    }
    # Softmax turns the scores into a probability distribution.
    probabilities = softmax(list(logits.values()))
    distribution = dict(zip(VOCAB, probabilities))
    # Greedy decoding selects the largest probability. Real inference can use
    # temperature, top-k, or top-p sampling.
    selected = max(distribution, key=distribution.get)

    print("STEP 5 · LOGITS → PROBABILITIES → NEXT TOKEN")
    print("=" * 52)
    print("Layer output hidden vector:", HIDDEN)
    print()
    print("Output weight dot products:")
    for token in VOCAB:
        weights = OUTPUT_WEIGHTS[token]
        print(f"  {token:6} {HIDDEN} · {weights} = {logits[token]:+.3f}")
    print()
    print("Logits:", [round(logits[token], 3) for token in VOCAB])
    print("Probabilities:")
    for token in VOCAB:
        print(f"  {token:6} → {distribution[token]:.2%}")
    print()
    print("ASCII FLOW")
    print("Layer output → output weights → logits → softmax")
    print("             → probabilities → choose next token")
    print()
    print(f"SELECTED NEXT TOKEN: {selected!r}")
    print("TEST PASS: Step 5 next-token calculation is deterministic.")

    assert selected == "."
    assert abs(sum(distribution.values()) - 1.0) < 1e-12
    assert max(distribution, key=distribution.get) == "."


if __name__ == "__main__":
    main()
