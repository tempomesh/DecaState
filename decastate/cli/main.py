"""DecaState command-line interface."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import typer

from decastate.cli.doctor import doctor_report
from decastate.runtime.ollama import OllamaRuntime
from decastate.state.capsule import StateCapsule
from decastate.checkpoint.manager import CheckpointError, CheckpointManager
from decastate.fork.manager import ForkError, ForkManager
from decastate.state.workspace import NativeWorkspace, NativeWorkspaceError
from mlx_lm.models.cache import load_prompt_cache, save_prompt_cache

app = typer.Typer(help="DecaState: local AI state runtime")


def _home() -> Path:
    return Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate"))


def _repo_context(repo: Path) -> str:
    """Build a bounded, real repository context for the developer wedge."""
    repo = repo.resolve()
    selected = [
        repo / "README.md", repo / "pyproject.toml", repo / "Makefile",
        repo / "docs" / "ARCHITECTURE.md", repo / "docs" / "ROADMAP.md",
    ]
    selected.extend(sorted((repo / "decastate").glob("**/*.py"))[:10])
    chunks = [f"You are analyzing the repository at {repo}. Understand its architecture and state lifecycle.\n"]
    for path in selected:
        if path.is_file():
            try:
                relative = path.relative_to(repo)
            except ValueError:
                relative = path.name
            chunks.append(f"\n===== {relative} =====\n{path.read_text(errors='replace')}\n")
    return "".join(chunks)


@app.command()
def init() -> None:
    """Initialize the local DecaState runtime home."""
    home = _home()
    for name in ("states", "branches", "checkpoints", "contexts", "locks"):
        (home / name).mkdir(parents=True, exist_ok=True)
    print(json.dumps({"initialized": True, "home": str(home), "runtime": "local-native-mlx"}, indent=2))


@app.command()
def understand(
    repo: Path = typer.Argument(Path("."), exists=True, file_okay=False, readable=True),
    model: str = typer.Option("mlx-community/Qwen2.5-0.5B-Instruct-4bit"),
    state_id: str | None = typer.Option(None, help="Optional stable state name."),
) -> None:
    """Understand a real repository once and persist its native MLX state."""
    repo = repo.resolve()
    state_id = state_id or f"repo-{repo.name}-{int(time.time())}"
    home = _home()
    context_path = home / "contexts" / f"{state_id}.txt"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(_repo_context(repo))
    try:
        workspace = NativeWorkspace.create(state_id, model, context_path)
        active = {"state_id": state_id, "repo": str(repo), "model": model,
                  "created_at": time.time(), "workflow": "coding-agent"}
        (home / "active.json").write_text(json.dumps(active, indent=2) + "\n")
        result = workspace.status()
        result["repo"] = str(repo)
        result["next"] = [f"decastate checkpoint {state_id} repo-ready",
                           f"decastate fork {state_id} reviewer"]
        print(json.dumps(result, indent=2))
    except (NativeWorkspaceError, OSError, KeyError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def doctor() -> None:
    """Inspect local hardware, dependencies, and model availability."""
    doctor_report()


@app.command()
def gateway(
    port: int = typer.Option(8787, help="Local port for the gateway."),
    upstream: str = typer.Option("https://api.anthropic.com", help="Provider base URL."),
    inject_cache: bool = typer.Option(False, "--inject-cache",
                                      help="Add cache_control for clients that don't cache "
                                           "(content never altered; reported honestly)."),
) -> None:
    """Run the honest API gateway: byte-identical forwarding + provider-cache audit."""
    from decastate.gateway.proxy import run_gateway

    run_gateway(port=port, upstream=upstream, inject_cache=inject_cache)


@app.command()
def savings() -> None:
    """Show cumulative provider-cache savings measured by the gateway (real requests only)."""
    from decastate.gateway.proxy import print_savings, savings_summary

    print_savings(savings_summary())


@app.command("gateway-selftest")
def gateway_selftest() -> None:
    """Verify gateway plumbing (byte-identical forward + usage extraction) with a local echo."""
    from decastate.gateway.proxy import run_selftest

    result = run_selftest()
    if not result["passed"]:
        raise typer.Exit(code=1)


@app.command()
def demo(
    repo: Path = typer.Argument(Path("."), exists=True, file_okay=False, readable=True),
    model: str = typer.Option("mlx-community/Qwen2.5-0.5B-Instruct-4bit"),
) -> None:
    """Understand a repository once, checkpoint, wake, and fork — all measured live."""
    from decastate.cli.demo_cmd import run_demo

    try:
        run_demo(repo, model_id=model)
    except (OSError, KeyError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("create")
def create_state(
    state_id: str = typer.Argument(...),
    context_file: Path = typer.Option(..., exists=True, readable=True),
    model: str = typer.Option("mlx-community/Qwen2.5-0.5B-Instruct-4bit"),
) -> None:
    """Build and persist a native MLX state from a context file."""
    try:
        print(json.dumps(NativeWorkspace.create(state_id, model, context_file).status(), indent=2))
    except (NativeWorkspaceError, OSError, KeyError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("continue")
def continue_state(
    state_id: str = typer.Argument(...),
    prompt: str = typer.Argument(...),
    max_tokens: int = typer.Option(32),
) -> None:
    """Continue a native MLX state and persist the updated state."""
    try:
        workspace = NativeWorkspace.from_env(state_id)
        print(workspace.continue_generation(prompt, max_tokens=max_tokens))
    except (NativeWorkspaceError, OSError, KeyError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("status")
def state_status(state_id: str = typer.Argument(...)) -> None:
    """Inspect a native MLX state workspace."""
    try:
        print(json.dumps(NativeWorkspace.from_env(state_id).status(), indent=2))
    except (NativeWorkspaceError, OSError, KeyError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Prompt to send to the local model."),
    model: str = typer.Option("qwen2.5:14b", help="Existing Ollama model name."),
) -> None:
    """Run a local Ollama smoke test using an existing model."""
    print(OllamaRuntime(model=model).generate(prompt))


@app.command()
def inspect(state: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Inspect a DecaState metadata capsule."""
    print(json.dumps(StateCapsule.load(state).manifest, indent=2))


@app.command()
def save(
    state: Path = typer.Argument(..., help="Destination metadata capsule."),
    model: str = typer.Option("qwen2.5:14b"),
) -> None:
    """Create metadata only; never claim Ollama context is native persisted state."""
    capsule = StateCapsule.create_ollama_metadata(state, model=model)
    print(f"metadata capsule created: {capsule.path}")
    print("NOTE: Ollama native inference state was not captured or persisted.")


@app.command()
def wake(state: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Refuse unsafe restore when a capsule has no native state."""
    capsule = StateCapsule.load(state)
    if capsule.manifest.get("restore", {}).get("supported") is not True:
        raise typer.BadParameter("This capsule has no native restore state; wake is unavailable.")


def _native_workspace(state_id: str) -> tuple[Path, Path, dict]:
    home = Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate"))
    state_dir = home / "states" / state_id
    manifest_path = state_dir / "manifest.json"
    live_path = state_dir / "live-cache.safetensors"
    if not manifest_path.exists() or not live_path.exists():
        raise typer.BadParameter(
            f"native live state not found for {state_id}; expected {live_path} and {manifest_path}"
        )
    return home, live_path, json.loads(manifest_path.read_text())


@app.command()
def checkpoint(
    state_id: str = typer.Argument(...),
    checkpoint_name: str = typer.Argument(...),
) -> None:
    """Save the current native MLX live cache as an immutable checkpoint."""
    try:
        home, live_path, manifest = _native_workspace(state_id)
        cache, _ = load_prompt_cache(str(live_path), return_metadata=True)
        manager = CheckpointManager(home, state_id, manifest["model"]["id"])
        created = manager.create(checkpoint_name, cache, int(manifest["context"]["token_count"]),
                                 provenance={"operation": "checkpoint", "source": str(live_path)})
        print(json.dumps(created, indent=2))
    except (CheckpointError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("checkpoints")
def list_checkpoints(state_id: str = typer.Argument(...)) -> None:
    """List immutable checkpoints and their lineage."""
    try:
        home, _live_path, manifest = _native_workspace(state_id)
        print(json.dumps(CheckpointManager(home, state_id, manifest["model"]["id"]).list(), indent=2))
    except (CheckpointError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def rollback(
    state_id: str = typer.Argument(...),
    checkpoint_name: str = typer.Argument(...),
) -> None:
    """Restore a named native checkpoint into the live state workspace."""
    try:
        home, live_path, manifest = _native_workspace(state_id)
        manager = CheckpointManager(home, state_id, manifest["model"]["id"])
        cache, checkpoint_manifest = manager.load(checkpoint_name, expected_model_id=manifest["model"]["id"])
        save_prompt_cache(str(live_path), cache, {"model_id": manifest["model"]["id"],
                                                 "restored_checkpoint_id": checkpoint_manifest["checkpoint_id"]})
        manifest["context"]["token_count"] = checkpoint_manifest["context"]["token_count"]
        manifest["context"]["cache_position"] = checkpoint_manifest["context"]["cache_position"]
        manifest["live_checkpoint_id"] = checkpoint_manifest["checkpoint_id"]
        (live_path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps({"restored": checkpoint_name, "checkpoint_id": checkpoint_manifest["checkpoint_id"]}, indent=2))
    except (CheckpointError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def fork(
    state_id: str = typer.Argument(..., help="State ID, or branch name when an active state exists."),
    branch_name: str | None = typer.Argument(None),
) -> None:
    """Create a physical-copy native MLX branch from the live state."""
    try:
        if branch_name is None:
            branch_name = state_id
            active_path = _home() / "active.json"
            if not active_path.exists():
                raise ForkError("no active state; run `decastate understand .` first")
            state_id = json.loads(active_path.read_text())["state_id"]
        home, live_path, manifest = _native_workspace(state_id)
        created = ForkManager(home, state_id, manifest["model"]["id"]).create(
            branch_name, live_path, int(manifest["context"]["token_count"])
        )
        print(json.dumps(created, indent=2))
    except (ForkError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


if __name__ == "__main__":
    app()
