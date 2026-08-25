from decastate.runtime.ollama import OllamaRuntime


def test_runtime_info() -> None:
    info = OllamaRuntime("qwen2.5:14b").runtime_info()
    assert info["name"] == "ollama"
    assert info["model"] == "qwen2.5:14b"
