"""STEP 2 LESSON — one embedding becomes Q, K, and V.

Step 1 produced a vector for each token. Here the model makes three views of
that same vector:

    Q (Query) = what the current token is looking for
    K (Key)   = what a token advertises for matching
    V (Value) = information a token contributes if selected

WQ, WK, and WV are weight matrices. They are hand-written and tiny here so a
beginner can inspect every number. Real training learns much larger matrices.
This shows the mechanism underneath Qwen/MLX; it is not Qwen itself.
"""
from __future__ import annotations


# These tokens participate in the attention example.
TOKENS = ["I", "like", "tea"]
# Tiny teaching embeddings. Step 1 taught us why text must become vectors.
EMBEDDINGS = {
    "I": [1.0, 0.0],
    "like": [0.0, 1.0],
    "tea": [1.0, 1.0],
}

# Real training learns these weights. We choose them by hand for clarity.
WQ = [[1.0, 0.0], [0.0, 1.0]]
WK = [[1.0, 0.0], [0.0, 1.0]]
WV = [[0.5, 0.0], [0.0, 2.0]]


def matvec(vector: list[float], matrix: list[list[float]]) -> list[float]:
    """Multiply a vector by a matrix: a small feature transformation."""
    return [sum(vector[row] * matrix[row][column] for row in range(len(vector)))
            for column in range(len(matrix[0]))]


def dot(left: list[float], right: list[float]) -> float:
    """Measure how strongly two vectors point in the same direction."""
    return sum(a * b for a, b in zip(left, right))


def main() -> None:
    # Gather one embedding vector for each token.
    embeddings = [EMBEDDINGS[token] for token in TOKENS]
    # The same input gets three different views: question, matching label,
    # and useful content.
    queries = [matvec(vector, WQ) for vector in embeddings]
    keys = [matvec(vector, WK) for vector in embeddings]
    values = [matvec(vector, WV) for vector in embeddings]

    print("STEP 2 · EMBEDDINGS → Q/K/V")
    print("=" * 44)
    print("Tokens:", TOKENS)
    print()
    for token, embedding, query, key, value in zip(
        TOKENS, embeddings, queries, keys, values
    ):
        print(f"{token:5} embedding={embedding}  Q={query}  K={key}  V={value}")

    # "tea" is the current token. Its query asks which keys are relevant.
    current_query = queries[-1]
    scores = [dot(current_query, key) for key in keys]
    print()
    print("Current token: tea")
    print("Q(tea) compares with each K:")
    for token, key, score in zip(TOKENS, keys, scores):
        print(f"  Q(tea) · K({token}) = {score:+.2f}")

    print()
    print("ASCII FLOW")
    print("  token → embedding → multiply by WQ/WK/WV → Q/K/V")
    print("                                      │")
    print("                                      ├─ Q asks: what matters now?")
    print("                                      ├─ K says: what does each token contain?")
    print("                                      └─ V carries: what information can be used?")
    print()
    print("KV CACHE CONNECTION")
    print("  after processing 'I like': save K(I), K(like), V(I), V(like)")
    print("  for 'tea': create Q(tea), read old K/V, then append K(tea), V(tea)")

    assert queries[0] == [1.0, 0.0]
    assert keys[1] == [0.0, 1.0]
    assert values[1] == [0.0, 2.0]
    print("\nTEST PASS: Step 2 Q/K/V calculation is deterministic.")


if __name__ == "__main__":
    main()
