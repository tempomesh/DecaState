# DecaState dashboard

This is the investor-facing local dashboard for the AI State Runtime. It is intentionally evidence-led: all headline numbers mirror the real MLX benchmark artifacts in `benchmarks/results/` and the UI clearly marks the current physical-copy fork boundary.

Run it from the repository root:

```bash
make ui
```

Then open http://127.0.0.1:4173/ui/.

The dashboard supports the coding-agent wedge, but it is not the product itself. The product workflow is the CLI: `init`, `understand`, `checkpoint`, and `fork` against a real repository.
