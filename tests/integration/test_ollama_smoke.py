import os

import pytest

from decastate.runtime.ollama import OllamaRuntime


@pytest.mark.integration
def test_existing_qwen_smoke() -> None:
    if os.environ.get("DECASTATE_RUN_MODEL_TESTS") != "1":
        pytest.skip("set DECASTATE_RUN_MODEL_TESTS=1 to run model inference")
    assert "DECASTATE_OLLAMA_OK" in OllamaRuntime().generate(
        "Reply with exactly: DECASTATE_OLLAMA_OK"
    )
