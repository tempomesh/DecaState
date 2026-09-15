"""STEP 1 LESSON — turn a sentence into numbers.

A real LLM cannot do arithmetic directly on the letters in ``"I like tea"``.
It first breaks text into tokens, gives every token an ID, and looks up a
vector of numbers for every ID. Those vectors enter the transformer.

English text -> tokens -> integer IDs -> embedding vectors.

This file deliberately stops there: no Q/K/V, attention, training, MLX, API,
or GPU yet.
"""
from __future__ import annotations


# A vocabulary is the model's dictionary. Real vocabularies are much larger
# and may contain pieces of words rather than whole words.
VOCAB = ["<BOS>", "I", "like", "tea", "coffee", ".", "<UNK>"]
# An ID is the token's address in the dictionary, not an importance score.
TOKEN_ID = {token: i for i, token in enumerate(VOCAB)}

# This is the embedding table: token -> vector. These values are hand-made
# for teaching; training learns real values with many more dimensions.
EMBEDDINGS = {
    "<BOS>": [0.00, 0.00, 0.00, 1.00],
    "I": [1.00, 0.00, 0.00, 0.10],
    "like": [0.00, 1.00, 0.00, 0.20],
    "tea": [0.00, 0.00, 1.00, 0.30],
    "coffee": [0.00, 0.00, -1.00, 0.30],
    ".": [0.00, 0.00, 0.00, 0.40],
    "<UNK>": [0.00, 0.00, 0.00, 0.00],
}


def tokenize(text: str) -> list[str]:
    """Split this lesson's text and add BOS (beginning of sequence)."""
    words = text.strip().split()
    return ["<BOS>", *words]


def main() -> None:
    # This running sentence is reused in the later lessons.
    text = "I like tea"
    tokens = tokenize(text)
    # Unknown words receive UNK instead of causing a lookup failure.
    ids = [TOKEN_ID.get(token, TOKEN_ID["<UNK>"]) for token in tokens]
    # Embedding lookup: use each token ID as an address in the table.
    vectors = [EMBEDDINGS[VOCAB[token_id] if token_id < len(VOCAB) else "<UNK>"] for token_id in ids]

    print("STEP 1 · TEXT → TOKENS → EMBEDDINGS")
    print("=" * 48)
    print(f"Text: {text!r}")
    print()
    print("Vocabulary:")
    for token_id, token in enumerate(VOCAB):
        print(f"  {token_id}: {token}")
    print()
    print("Sequence entering the transformer:")
    print("position   token       token ID   embedding (4 numbers)")
    for position, (token, token_id, vector) in enumerate(zip(tokens, ids, vectors)):
        print(f"{position:>8}   {token:<10} {token_id:>8}   {vector}")
    print()
    print("WHAT THIS MEANS")
    print("  Words are not sent directly into the neural network.")
    print("  The tokenizer gives each piece an ID.")
    print("  The embedding table turns each ID into numbers.")
    print("  These vectors are the input to the first transformer layer.")
    print()
    print("NOT YET")
    print("  No Q/K/V has been created yet.")
    print("  No attention has happened yet.")
    print("  No answer has been generated yet.")
    print()
    print("ASCII FLOW")
    print("  'I like tea'")
    print("       │")
    print("       ▼")
    print("  ['<BOS>', 'I', 'like', 'tea']")
    print("       │ tokenizer")
    print("       ▼")
    print("  [0, 1, 2, 3]")
    print("       │ embedding lookup")
    print("       ▼")
    print("  [[0,0,0,1], [1,0,0,.1], [0,1,0,.2], [0,0,1,.3]]")
    print("       │")
    print("       ▼")
    print("  next lesson: transformer layer creates Q, K, and V")

    assert tokens == ["<BOS>", "I", "like", "tea"]
    assert ids == [0, 1, 2, 3]
    assert len(vectors) == 4 and all(len(vector) == 4 for vector in vectors)
    print("\nTEST PASS: Step 1 tokenization and embeddings are deterministic.")


if __name__ == "__main__":
    main()
