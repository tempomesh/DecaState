"""STEP 11 LESSON — generate multiple tokens one at a time.

An LLM does not normally write the entire answer in one calculation. It:

    reads the current context -> chooses one token -> appends it -> repeats

This tiny deterministic policy makes that loop visible using our sentence
``I like tea``. The policy is deliberately simple; the real Qwen model uses
its transformer and probabilities at every iteration.
"""
from __future__ import annotations


NEXT_TOKEN = {
    ("I",): "like",
    ("I", "like"): "tea",
    ("I", "like", "tea"): ".",
}


def generate(prefix: list[str], max_new_tokens: int) -> list[str]:
    """Append one predicted token at a time and return the full sequence."""
    tokens = prefix.copy()
    for _ in range(max_new_tokens):
        context = tuple(tokens)
        next_token = NEXT_TOKEN.get(context, "<END>")
        print(f"context={tokens!r} → next token={next_token!r}")
        tokens.append(next_token)
        if next_token == "<END>":
            break
    return tokens


def main() -> None:
    print("STEP 11 · AUTOREGRESSIVE GENERATION")
    print("=" * 58)
    print("ASCII LOOP")
    print("  prompt → model → one token")
    print("              │")
    print("              └── append token to context and repeat")
    print()
    result = generate(["I"], max_new_tokens=4)
    print()
    print("FINAL TOKEN SEQUENCE:", result)
    print("FINAL TEXT:", " ".join(result))
    print()
    print("PREFILL versus DECODE")
    print("  first prompt read = prefill")
    print("  each new token    = decode step")
    print("  each decode step can append new K/V to the cache")
    assert result == ["I", "like", "tea", ".", "<END>"]
    print("\nTEST PASS: generation appends one token at a time.")


if __name__ == "__main__":
    main()
