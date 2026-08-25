"""One-command product demo: understand a repository once, then never rebuild it."""
from __future__ import annotations

import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache, save_prompt_cache
from rich.console import Console
from rich.table import Table

from decastate.checkpoint.manager import CheckpointManager
from decastate.fork.manager import ForkManager

DEFAULT_MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
CONTEXT_TOKEN_CAP = 2048
SOURCE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java", ".rb", ".c", ".cc", ".cpp", ".h", ".swift")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".decastate", "dist", "build", ".next", "target"}


def collect_repo_files(repo: Path, max_files: int = 24) -> list[Path]:
    """Select a bounded, real set of files that describe a repository."""
    picked: list[Path] = []
    for name in ("README.md", "README.rst", "pyproject.toml", "package.json", "go.mod",
                 "Cargo.toml", "Makefile", "ARCHITECTURE.md"):
        candidate = repo / name
        if candidate.is_file():
            picked.append(candidate)
    docs = repo / "docs"
    if docs.is_dir():
        picked.extend(sorted(p for p in docs.glob("*.md") if p.is_file())[:4])
    sources: list[Path] = []
    for path in sorted(repo.rglob("*")):
        if len(sources) >= max_files:
            break
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        sources.append(path)
    return (picked + sources)[:max_files]


def build_repo_context(repo: Path, char_budget: int = 24000) -> tuple[str, list[str]]:
    files = collect_repo_files(repo)
    chunks = [f"You are analyzing the repository at {repo.name}. Understand its architecture, "
              "purpose, and how its pieces fit together.\n"]
    included: list[str] = []
    used = 0
    for path in files:
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        relative = str(path.relative_to(repo))
        remaining = char_budget - used
        if remaining <= 0:
            break
        snippet = text[:remaining]
        chunks.append(f"\n===== {relative} =====\n{snippet}\n")
        included.append(relative)
        used += len(snippet)
    return "".join(chunks), included


def run_demo(repo: Path, model_id: str = DEFAULT_MODEL) -> dict:
    console = Console()
    repo = repo.resolve()
    console.print(f"\n[bold]DECASTATE DEMO[/bold] — persistent AI state for [cyan]{repo.name}[/cyan]\n")

    console.print("[dim]loading model (one-time, not counted in benchmarks)…[/dim]")
    model, tokenizer = load(model_id)

    context_text, included_files = build_repo_context(repo)
    tokens = tokenizer.encode(context_text, add_special_tokens=True)[:CONTEXT_TOKEN_CAP]
    prefix, probe = tokens[:-1], tokens[-1]
    truncated = len(tokenizer.encode(context_text, add_special_tokens=True)) > CONTEXT_TOKEN_CAP

    # [1/5] Understand the repository once (real prefill into a native MLX cache).
    started = time.perf_counter()
    cache = make_prompt_cache(model)
    list(generate_step(mx.array(prefix, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cache))
    mx.eval([c.state for c in cache])
    understand_seconds = time.perf_counter() - started
    console.print(f"[green]✓[/green] [1/5] Understood repository: {len(included_files)} files, "
                  f"{len(prefix):,} tokens of native MLX state in {understand_seconds*1000:.0f} ms"
                  + (" [dim](context capped at 2,048 tokens for the proof model)[/dim]" if truncated else ""))

    state_root = repo / ".decastate"
    state_id = f"demo-{int(time.time() * 1000)}"
    state_dir = state_root / "states" / state_id
    state_dir.mkdir(parents=True, exist_ok=True)
    base_path = state_dir / "live-cache.safetensors"
    save_prompt_cache(str(base_path), cache, {"model_id": model_id, "state_id": state_id})
    (state_dir / "manifest.json").write_text(json.dumps({
        "model": {"id": model_id},
        "context": {"token_count": len(prefix), "cache_position": int(cache[0].offset)},
    }, indent=2) + "\n")

    # [2/5] Immutable checkpoint.
    checkpoints = CheckpointManager(state_root, state_id, model_id)
    checkpoint = checkpoints.create("repo-understood", cache, len(prefix),
                                    provenance={"demo": "decastate-demo", "repo": repo.name})
    console.print(f"[green]✓[/green] [2/5] Checkpoint 'repo-understood': "
                  f"{checkpoint['state_size_bytes']/1e6:.1f} MB immutable native state "
                  f"({checkpoint['creation_seconds']*1000:.0f} ms)")

    # [3/5] Cold rebuild vs wake-from-disk, exact-token comparison.
    def continuation(active_cache, count=12):
        start = time.perf_counter()
        out = [int(t) for t, _ in generate_step(mx.array([probe], dtype=mx.uint32), model,
                                                max_tokens=count, prompt_cache=active_cache)]
        return out, time.perf_counter() - start

    cold_start = time.perf_counter()
    cold_cache = make_prompt_cache(model)
    list(generate_step(mx.array(prefix, dtype=mx.uint32), model, max_tokens=0, prompt_cache=cold_cache))
    mx.eval([c.state for c in cold_cache])
    cold_tokens, cold_gen = continuation(cold_cache)
    cold_total = time.perf_counter() - cold_start

    wake_start = time.perf_counter()
    wake_cache, _ = checkpoints.load("repo-understood")
    wake_tokens, wake_gen = continuation(wake_cache)
    wake_total = time.perf_counter() - wake_start

    exact = cold_tokens == wake_tokens
    speedup = cold_total / wake_total if wake_total else 0.0
    console.print(f"[green]✓[/green] [3/5] Cold rebuild {cold_total*1000:.0f} ms vs wake {wake_total*1000:.0f} ms "
                  f"→ [bold]{speedup:.1f}× faster[/bold], 0/{len(prefix):,} context tokens re-read, "
                  f"exact continuation: {exact}")

    # [4/5] Fork into three agents.
    forks = ForkManager(state_root, state_id, model_id)
    roles = ("coder", "reviewer", "security")
    fork_rows = []
    for role in roles:
        manifest = forks.create(role, base_path, len(prefix))
        branch_path = state_root / "branches" / state_id / role / "native-cache.safetensors"
        branch_cache, _ = load_prompt_cache(str(branch_path), return_metadata=True)
        branch_tokens, _ = continuation(branch_cache, count=6)
        fork_rows.append({"role": role, "fork_ms": manifest["fork_seconds"] * 1000,
                          "size_mb": manifest["logical_state_size_bytes"] / 1e6,
                          "wake_exact": branch_tokens[:6] == cold_tokens[:6]})
    fork_ms = ", ".join(f"{r['role']} {r['fork_ms']:.0f} ms" for r in fork_rows)
    console.print(f"[green]✓[/green] [4/5] Forked 3 agents from one understood state: {fork_ms}")

    # [5/5] Summary.
    all_exact = exact and all(r["wake_exact"] for r in fork_rows)
    console.print(f"[green]✓[/green] [5/5] All continuations byte-exact: {all_exact} "
                  f"[dim](physical-copy forks; no COW claim)[/dim]\n")

    table = Table(title=f"decastate demo — {repo.name} ({model_id})")
    table.add_column("Metric"); table.add_column("Value", justify="right")
    table.add_row("Repository context", f"{len(prefix):,} tokens / {len(included_files)} files")
    table.add_row("Understand once (prefill)", f"{understand_seconds*1000:.0f} ms")
    table.add_row("Cold rebuild + continue", f"{cold_total*1000:.0f} ms")
    table.add_row("Wake from disk + continue", f"{wake_total*1000:.0f} ms")
    table.add_row("Resume speedup", f"{speedup:.1f}×")
    table.add_row("Context tokens re-read on wake", "0")
    table.add_row("Exact continuation", str(exact))
    table.add_row("Agents forked", "3 (coder / reviewer / security)")
    console.print(table)
    console.print("\n[dim]All numbers measured live on this machine, this run. State stored under "
                  f"{state_root}/[/dim]\n")

    result = {"repo": str(repo), "model_id": model_id, "state_id": state_id,
              "context_tokens": len(prefix), "files": included_files,
              "understand_seconds": understand_seconds, "cold_total_seconds": cold_total,
              "wake_total_seconds": wake_total, "resume_speedup": speedup,
              "cold_vs_wake_exact": exact, "branches": fork_rows,
              "claim_boundary": "physical-copy forks; no COW or portability claim"}
    results_dir = state_root / "demo-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{state_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
