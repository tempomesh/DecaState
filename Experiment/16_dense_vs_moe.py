"""Step 16 — dense MLP versus a Mixture-of-Experts MLP.

Run with: make step16. Attention moves information between positions; the MLP
processes each position. Dense and MoE are two ways to implement that MLP.
"""


def softmax(values):
    top = max(values)
    exp_values = [2.718281828 ** (v - top) for v in values]
    total = sum(exp_values)
    return [v / total for v in exp_values]


def main():
    experts = ["code", "language", "numbers", "planning"]
    scores = [2.2, 0.4, 1.7, 0.1]
    ranking = sorted(zip(softmax(scores), experts), reverse=True)
    print("STEP 16 — DENSE MLP vs MoE")
    print("Running example: after attention mixes `I`, `like`, and `tea`, the MLP refines tea's vector.")
    print("The router may send the tea vector to language and numbers experts.")
    print("DENSE: every token uses the same learned MLP weights")
    print("MOE:   every token -> learned router -> a few specialist MLPs")
    for probability, expert in ranking:
        print(f"{expert:>8}: router probability {probability:.1%}")
    print("Top-2 active experts:", ", ".join(expert for _, expert in ranking[:2]))
    print("The router learns during training; inference performs arithmetic and routes.")
    print("MoE may have more total parameters but fewer active parameters per token.")
    print("STEP 16 COMPLETE")


if __name__ == "__main__":
    main()
