"""Entry point for curriculum Step 1 from the Experiment directory."""

from pathlib import Path
import runpy


runpy.run_path(
    str(Path(__file__).parents[1] / "experiments" / "08_step1_tokens_embeddings.py"),
    run_name="__main__",
)
