"""STEP 10 LESSON — train tiny Q/K/V attention parameters.

Step 6 trained an output head. Here the trainable parameters are the scalar
teaching versions of WQ, WK, WV, and WO. We use a numerical gradient because
it is easier to see than a full automatic-differentiation engine:

    slightly change one parameter -> measure loss change -> update it

Real LLM training uses automatic differentiation and millions/billions of
parameters. This tiny script demonstrates the same direction of learning.
"""
from __future__ import annotations

import math


TOKENS = ["I", "like", "tea", "coffee"]
EMBEDDINGS = {"I": 0.2, "like": 0.8, "tea": 1.0, "coffee": -0.6}
PREFIX = ["I", "like"]
TARGET = "tea"
OUTPUT_EMBEDDINGS = {"I": 0.1, "like": 0.2, "tea": 1.0, "coffee": -0.2}
PARAMETERS = {"WQ": 0.20, "WK": 0.20, "WV": 0.20, "WO": 0.20}
LEARNING_RATE = 0.8
EPSILON = 1e-4
STEPS = 40


def softmax(values: list[float]) -> list[float]:
    peak = max(values)
    exponentials = [math.exp(value - peak) for value in values]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def forward(parameters: dict[str, float]) -> list[float]:
    """Create Q/K/V, perform attention, and return next-token logits."""
    query = EMBEDDINGS[PREFIX[-1]] * parameters["WQ"]
    keys = [EMBEDDINGS[token] * parameters["WK"] for token in PREFIX]
    values = [EMBEDDINGS[token] * parameters["WV"] for token in PREFIX]
    scores = [query * key for key in keys]
    attention = softmax(scores)
    attended = sum(weight * value for weight, value in zip(attention, values))
    hidden = attended * parameters["WO"]
    return [hidden * OUTPUT_EMBEDDINGS[token] for token in TOKENS]


def loss(parameters: dict[str, float]) -> float:
    """Measure how unlikely the correct next token is."""
    probabilities = softmax(forward(parameters))
    return -math.log(probabilities[TOKENS.index(TARGET)])


def numerical_gradient(parameters: dict[str, float], name: str) -> float:
    """Estimate d(loss)/d(parameter) by trying a tiny plus/minus change."""
    plus = parameters.copy()
    minus = parameters.copy()
    plus[name] += EPSILON
    minus[name] -= EPSILON
    return (loss(plus) - loss(minus)) / (2 * EPSILON)


def main() -> None:
    parameters = PARAMETERS.copy()
    print("STEP 10 · TRAIN TINY Q/K/V ATTENTION")
    print("=" * 58)
    print("Target example:", " ".join(PREFIX), "→", TARGET)
    print("ASCII UPDATE")
    print("  WQ/WK/WV/WO")
    print("       │")
    print("       ▼ forward: Q/K/V → attention → logits")
    print("       │")
    print("       ▼ loss for the target token 'tea'")
    print("       │")
    print("       ▼ numerical gradients → update WQ/WK/WV/WO")
    print()
    first = loss(parameters)
    for step in range(1, STEPS + 1):
        gradients = {name: numerical_gradient(parameters, name) for name in parameters}
        for name, gradient in gradients.items():
            parameters[name] -= LEARNING_RATE * gradient
        if step == 1 or step % 10 == 0:
            print(f"step {step:02d}: loss={loss(parameters):.4f}  params={parameters}")
    final = loss(parameters)
    print()
    print("WHAT CHANGED")
    print("  The attention parameters moved so the target token became more likely.")
    print("  In a real model, automatic backpropagation replaces this slow numerical gradient.")
    print("  K/V cache is still inference state; these W parameters are learned weights.")
    print(f"loss before: {first:.4f}")
    print(f"loss after:  {final:.4f}")
    assert final < first
    print("\nTEST PASS: training reduced loss by changing Q/K/V attention parameters.")


if __name__ == "__main__":
    main()
