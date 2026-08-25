from pathlib import Path

from decastate.state.capsule import StateCapsule


def test_ollama_capsule_is_explicitly_not_restorable(tmp_path: Path) -> None:
    capsule = StateCapsule.create_ollama_metadata(tmp_path / "state.dstate", "qwen2.5:14b")
    loaded = StateCapsule.load(capsule.path)
    assert loaded.manifest["restore"]["supported"] is False
