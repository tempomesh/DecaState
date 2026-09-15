"""Step 14 — attention types and causal masking.

Run with: make step14

The attention operation is Q/K/V math. The attention type is the rule that
decides which positions may look at which other positions.
"""


def show_matrix(title, tokens, allowed):
    print(f"\n{title}")
    print("          " + "  ".join(f"{t:>5}" for t in tokens))
    for token, row in zip(tokens, allowed):
        cells = "  ".join("YES" if value else "NO " for value in row)
        print(f"{token:>8}  {cells}")


def main():
    tokens = ["I", "like", "tea"]
    causal = [[col <= row for col in range(3)] for row in range(3)]
    bidirectional = [[True] * 3 for _ in range(3)]
    local_window = [[abs(col - row) <= 1 for col in range(3)] for row in range(3)]
    print("STEP 14 — ATTENTION TYPES")
    print("Self-attention: tokens look at tokens in the same sequence.")
    show_matrix("Causal self-attention: an LLM cannot see future tokens", tokens, causal)
    show_matrix("Bidirectional self-attention: tokens may see left and right", tokens, bidirectional)
    show_matrix("Local/window attention: tokens see nearby positions", tokens, local_window)
    print("\nCross-attention: answer tokens ask questions about a separate document sequence.")
    print("The causal mask is a rule, not a human-like decision by the model.")
    print("STEP 14 COMPLETE")


if __name__ == "__main__":
    main()
