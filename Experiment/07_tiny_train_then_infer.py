"""STEP 7 LESSON — train a tiny model, then use it for inference.

This file deliberately places both phases next to each other:

    TRAINING:  examples + correct answers -> loss -> gradients -> new weights
    INFERENCE: prompt + frozen weights -> probabilities -> predicted token

The model is a tiny next-token classifier. It has a small hidden vector for
each teaching context and a trainable output matrix. It is "LLM-like" because
it predicts the next token from a numeric representation and uses softmax,
loss, and gradient descent. It is not a useful general LLM: it does not have a
real tokenizer, transformer stack, learned Q/K/V, or broad training corpus.

That limitation is intentional. It makes the boundary between learning and
answering visible before we add the real KV-cache experiment.
"""
from __future__ import annotations

import math


TOKENS = ["I", "like", "tea", "coffee"]
TOKEN_ID = {token: index for index, token in enumerate(TOKENS)}

# These are fixed teaching representations standing in for the output of a
# transformer. In a real model, the transformer would calculate them from the
# whole prompt using embeddings, Q/K/V, attention, MLPs, and learned weights.
TRAINING_EXAMPLES = [
    ("I", [1.0, 0.0], "like"),
    ("I like", [-1.0, 1.0], "tea"),
    ("like", [0.0, 1.0], "tea"),
]

# One output-weight row per possible next token. Training will change these
# numbers. Keeping the matrix small lets us print and understand the updates.
INITIAL_OUTPUT_WEIGHTS = [
    [0.20, 0.10],  # I
    [0.10, 0.20],  # like
    [-0.05, -0.05],  # tea
    [0.05, -0.05],  # coffee
]
LEARNING_RATE = 0.25
EPOCHS = 30


def softmax(scores: list[float]) -> list[float]:
    """Turn raw scores into probabilities that add up to one."""
    peak = max(scores)
    exponentials = [math.exp(score - peak) for score in scores]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def predict(hidden: list[float], weights: list[list[float]]) -> list[float]:
    """Run the output head: hidden vector -> logits -> probabilities."""
    logits = [
        sum(feature * weight for feature, weight in zip(hidden, row))
        for row in weights
    ]
    return softmax(logits)


def train_one(
    hidden: list[float], target_token: str, weights: list[list[float]]
) -> float:
    """Train on one example and return its loss.

    The target token supplies the teaching signal. The model does not invent
    the definition of "correct"; the training data tells it what token came
    next. The gradient then adjusts every output row automatically.
    """
    probabilities = predict(hidden, weights)
    target_index = TOKEN_ID[target_token]
    loss = -math.log(max(probabilities[target_index], 1e-12))

    # Softmax + cross-entropy has a compact gradient: prediction minus target.
    score_gradients = probabilities.copy()
    score_gradients[target_index] -= 1.0

    # Backpropagate the score error into each output weight. The chain is:
    # loss -> logits -> output weights. We intentionally stop at this small
    # output head so the lesson stays readable.
    for row_index, score_gradient in enumerate(score_gradients):
        for feature_index, feature in enumerate(hidden):
            weights[row_index][feature_index] -= (
                LEARNING_RATE * score_gradient * feature
            )
    return loss


def show_inference(prompt: str, hidden: list[float], weights: list[list[float]]) -> str:
    """Use frozen learned weights to answer a new prompt.

    Nothing is learned here. This is the normal inference phase: calculate a
    distribution, then choose the most likely next token.
    """
    probabilities = predict(hidden, weights)
    best_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    print(f"Prompt: {prompt!r}")
    print("Inference only — weights are now frozen.")
    for token, probability in sorted(
        zip(TOKENS, probabilities), key=lambda pair: -pair[1]
    ):
        print(f"  next token {token:7} → {probability:.2%}")
    print(f"PREDICTION: {TOKENS[best_index]!r}")
    return TOKENS[best_index]


def main() -> None:
    weights = [row.copy() for row in INITIAL_OUTPUT_WEIGHTS]

    print("STEP 7 · TRAIN A TINY MODEL, THEN RUN INFERENCE")
    print("=" * 58)
    print("ASCII OVERVIEW")
    print("  TRAINING: examples + answer")
    print("       ↓ forward prediction")
    print("       ↓ loss: how wrong?")
    print("       ↓ gradient: how to adjust weights?")
    print("       ↓ update weights")
    print("       └── repeat")
    print()
    print("  INFERENCE: new prompt + frozen weights")
    print("       ↓ prediction")
    print("       ↓ choose next token")
    print()

    print("TRAINING PHASE")
    print("Correct examples:")
    for prompt, _, target in TRAINING_EXAMPLES:
        print(f"  {prompt!r} → {target!r}")
    first_loss = None
    last_loss = None
    for epoch in range(1, EPOCHS + 1):
        losses = [
            train_one(hidden, target, weights)
            for _, hidden, target in TRAINING_EXAMPLES
        ]
        average_loss = sum(losses) / len(losses)
        first_loss = average_loss if first_loss is None else first_loss
        last_loss = average_loss
        if epoch == 1 or epoch % 5 == 0:
            print(f"  epoch {epoch:02d}: average loss={average_loss:.4f}")

    print()
    print("INFERENCE PHASE")
    prediction = show_inference("I like", [-1.0, 1.0], weights)
    print()
    print("WHAT THIS PROVES")
    print("  Training changed the output weights using labelled examples.")
    print("  Inference used those weights without changing them.")
    print("  In a real LLM, the hidden vector comes from the full transformer.")
    print("  In DecaState, the KV cache belongs to this inference phase.")
    print()
    print("NOT YET")
    print("  This does not train a useful general language model.")
    print("  It trains only a small output head over fixed teaching vectors.")

    assert first_loss is not None and last_loss is not None
    assert last_loss < first_loss
    assert prediction == "tea"
    print("\nTEST PASS: training improved weights and inference predicted tea.")


if __name__ == "__main__":
    main()
