"""A tiny one-layer, ten-parameter language model for teaching Q/K/V.

This is intentionally not a useful language model. It is a transparent toy:
four one-number token embeddings, four scalar attention/output weights, and two
biases. It predicts the next token from the last token while attending to the
whole prefix. No model download, API key, MLX, or GPU is needed.
"""
from __future__ import annotations

import math


TOKENS = ["I", "like", "tea", "coffee"]
TOKEN_ID = {token: i for i, token in enumerate(TOKENS)}


# Exactly 10 parameters:
# 4 embeddings + WQ + WK + WV + WO + query_bias + key_bias.
PARAMETERS = {
    "E[I]": 0.20,
    "E[like]": 0.80,
    "E[tea]": 1.20,
    "E[coffee]": -1.00,
    "WQ": 1.00,
    "WK": 1.00,
    "WV": 1.00,
    "WO": 1.00,
    "query_bias": 0.00,
    "key_bias": 0.00,
}


def softmax(values: list[float]) -> list[float]:
    peak = max(values)
    exps = [math.exp(value - peak) for value in values]
    total = sum(exps)
    return [value / total for value in exps]


def run(prefix: list[str]) -> dict:
    p = PARAMETERS
    embeddings = [p[f"E[{token}]"] for token in prefix]
    query = embeddings[-1] * p["WQ"] + p["query_bias"]
    keys = [value * p["WK"] + p["key_bias"] for value in embeddings]
    values = [value * p["WV"] for value in embeddings]
    scores = [query * key for key in keys]  # Q × Kᵀ, scalar version
    weights = softmax(scores)
    attended = sum(weight * value for weight, value in zip(weights, values))
    hidden = attended * p["WO"]

    # Tied output embedding: no extra output matrix is needed in this toy.
    logits = {token: hidden * p[f"E[{token}]"] for token in TOKENS}
    probabilities = softmax(list(logits.values()))
    probs = dict(zip(TOKENS, probabilities))
    prediction = max(probs, key=probs.get)
    return {
        "prefix": prefix,
        "query": query,
        "keys": keys,
        "values": values,
        "scores": scores,
        "attention_weights": weights,
        "attended_value": attended,
        "hidden": hidden,
        "logits": logits,
        "probabilities": probs,
        "prediction": prediction,
    }


def show(result: dict) -> None:
    print("TINY 1-LAYER LLM · EXACTLY 10 PARAMETERS")
    print("=" * 48)
    print("Parameters:")
    for name, value in PARAMETERS.items():
        print(f"  {name:12} = {value:+.2f}")
    print(f"  total       = {len(PARAMETERS)}")
    print()
    print(f"Prompt: {' '.join(result['prefix'])}")
    print()
    print("One layer does:")
    print("  token embeddings → Q/K/V → attention → next-token prediction")
    print()
    print(f"Q (current token '{result['prefix'][-1]}') = {result['query']:+.4f}")
    print("Earlier token       K          V       Q×K score   attention")
    for token, key, value, score, weight in zip(
        result["prefix"], result["keys"], result["values"],
        result["scores"], result["attention_weights"]
    ):
        print(f"{token:16} {key:+.4f}   {value:+.4f}     {score:+.4f}       {weight:.1%}")
    print()
    print("attention = weighted sum of V")
    print(f"  attended value = {result['attended_value']:+.4f}")
    print()
    print("Next-token probabilities:")
    for token, probability in sorted(result["probabilities"].items(), key=lambda item: -item[1]):
        print(f"  {token:7} {probability:.1%}")
    print(f"PREDICTION: {result['prediction']}")
    print()
    print("ASCII FLOW")
    print("  'I like' → embeddings → Q₂='like' asks what matters")
    print("                    ↓")
    print("       Q₂ compares with K₁='I' and K₂='like'")
    print("                    ↓")
    print("       softmax creates attention percentages")
    print("                    ↓")
    print("       percentages mix V₁ and V₂")
    print("                    ↓")
    print("       tied output embedding predicts 'tea'")
    print()
    print("KV CACHE VERSION")
    print("  After 'I like': save K₁,K₂ and V₁,V₂")
    print("  Next token:    create Q₃, read saved K/V, append K₃,V₃")
    print("  DecaState:     saves/restores those K/V numbers")


def main() -> None:
    result = run(["I", "like"])
    show(result)
    assert len(PARAMETERS) == 10
    assert result["prediction"] == "tea"
    assert abs(sum(result["attention_weights"]) - 1.0) < 1e-9
    print("TEST PASS: one-layer attention and Q/K/V flow are deterministic.")


if __name__ == "__main__":
    main()
