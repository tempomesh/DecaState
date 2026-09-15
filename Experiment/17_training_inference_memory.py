"""Step 17 — training, inference, and memory-saving techniques.

Run with: make step17. Training changes weights; inference normally keeps
weights fixed and uses them to answer.
"""


def main():
    print("STEP 17 — TRAINING vs INFERENCE MEMORY")
    print("Running example: train on `I like tea` with the known next token, then ask the model to continue it.")
    print("TRAINING:  `I like tea` -> forward pass -> loss -> backpropagation -> updated weights")
    print("Training memory: weights + gradients + optimizer state + saved activations")
    print("INFERENCE: `I like tea` -> probabilities -> next token -> repeat")
    print("Inference memory: fixed weights + temporary activations + growing K/V cache")
    print("Activation checkpointing: save fewer activations, recompute some later.")
    print("Sharding: split tensors across devices. Offload: move selected data to CPU/storage.")
    print("Lower peak GPU memory can mean more compute or communication.")
    print("Backpropagation is for learning, not for every normal user question.")
    print("STEP 17 COMPLETE")


if __name__ == "__main__":
    main()
