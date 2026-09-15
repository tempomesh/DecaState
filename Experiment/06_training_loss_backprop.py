"""STEP 6 LESSON — loss, gradients, and learning.

The first five lessons used hand-written weights. A real language model needs
to improve its weights from examples. Training follows this loop:

    input -> prediction -> compare with correct answer -> loss
          -> gradients -> update weights -> try again

This file trains only a tiny output layer. The hidden vector is fixed, the
vocabulary has three tokens, and the correct answer is ``tea``. It is not a
useful LLM; it is a microscope for the idea of backpropagation.

Training changes model weights. Inference uses already-learned weights. The
later DecaState KV-cache lessons concern inference state; they do not replace
training and they do not change model weights.
"""
from __future__ import annotations

import math


# This is the tiny representation entering the output head, as in Step 5.
HIDDEN = [-1.0, 1.0]
VOCAB = ["I", "like", "tea"]
TARGET_INDEX = 2  # The correct answer in this teaching example is tea.

# One row per candidate token. These deliberately poor starting weights let us
# watch training increase the probability of tea.
WEIGHTS = [
    [0.20, 0.10],
    [0.10, 0.20],
    [-0.05, -0.05],
]
LEARNING_RATE = 0.40
STEPS = 12


def logits(weights: list[list[float]]) -> list[float]:
    """Score every candidate token with a dot product."""
    return [
        sum(hidden * weight for hidden, weight in zip(HIDDEN, row))
        for row in weights
    ]


def softmax(scores: list[float]) -> list[float]:
    """Convert raw scores into probabilities whose total is one."""
    peak = max(scores)
    exponentials = [math.exp(score - peak) for score in scores]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def cross_entropy(probabilities: list[float], target_index: int) -> float:
    """Measure how surprised the model is by the correct answer.

    High probability for tea means small loss. Low probability means large
    loss. The logarithm strongly penalizes being confidently wrong.
    """
    return -math.log(max(probabilities[target_index], 1e-12))


def gradients(probabilities: list[float], target_index: int) -> list[float]:
    """Calculate how each logit contributed to the error.

    For softmax plus cross-entropy, the teaching shortcut is predicted
    probability minus the one-hot target. A negative gradient says raise that
    score; a positive gradient says lower it.
    """
    result = probabilities.copy()
    result[target_index] -= 1.0
    return result


def update_weights(weights: list[list[float]], logit_gradients: list[float]) -> None:
    """Use gradient descent to move weights in the loss-reducing direction."""
    for row_index, gradient in enumerate(logit_gradients):
        for feature_index, feature in enumerate(HIDDEN):
            weights[row_index][feature_index] -= (
                LEARNING_RATE * gradient * feature
            )


def main() -> None:
    # Work on a copy so importing or rerunning this module never mutates the
    # example constants.
    weights = [row.copy() for row in WEIGHTS]

    print("STEP 6 · TRAINING: LOSS → GRADIENT → WEIGHT UPDATE")
    print("=" * 58)
    print("Input hidden vector:", HIDDEN)
    print("Correct next token:", VOCAB[TARGET_INDEX])
    print()
    print("ASCII TRAINING LOOP")
    print("  hidden vector + current weights")
    print("             │")
    print("             ▼")
    print("          logits → softmax probabilities")
    print("             │")
    print("             ▼")
    print("       compare with correct token")
    print("             │")
    print("             ▼")
    print("       loss → gradients → update weights")
    print("             │")
    print("             └──────── try again")
    print()

    first_loss = None
    last_loss = None
    for step in range(1, STEPS + 1):
        current_logits = logits(weights)
        probabilities = softmax(current_logits)
        loss = cross_entropy(probabilities, TARGET_INDEX)
        if first_loss is None:
            first_loss = loss
        last_loss = loss

        # Calculate the error signal before changing the weights.
        logit_gradients = gradients(probabilities, TARGET_INDEX)
        update_weights(weights, logit_gradients)

        print(
            f"step {step:02d}: loss={loss:.4f}  "
            f"I={probabilities[0]:.1%}  like={probabilities[1]:.1%}  "
            f"tea={probabilities[2]:.1%}"
        )

    final_probabilities = softmax(logits(weights))
    print()
    print("WHAT CHANGED")
    print("  The input and vocabulary stayed the same.")
    print("  The output weights changed so 'tea' became more likely.")
    print("  This is training: weights are updated before future inference.")
    print()
    print("FINAL PROBABILITIES")
    for token, probability in zip(VOCAB, final_probabilities):
        print(f"  {token:5} → {probability:.2%}")
    print()
    print("NOT YET")
    print("  This is not a full LLM training run.")
    print("  It does not train a tokenizer, transformer, or Q/K/V cache.")
    print("  It uses one example and one tiny output layer.")

    assert first_loss is not None and last_loss is not None
    assert last_loss < first_loss
    assert final_probabilities[TARGET_INDEX] > final_probabilities[0]
    print("\nTEST PASS: training reduced loss and increased target probability.")


if __name__ == "__main__":
    main()
