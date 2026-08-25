"""Small local Ollama adapter using the installed Ollama HTTP API."""
from __future__ import annotations
import json
import urllib.error
import urllib.request

class OllamaUnavailableError(RuntimeError):
    pass

class OllamaRuntime:
    def __init__(self, model: str = "qwen2.5:14b", endpoint: str = "http://127.0.0.1:11434"):
        self.model, self.endpoint = model, endpoint.rstrip("/")

    def generate(self, prompt: str) -> str:
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        request = urllib.request.Request(f"{self.endpoint}/api/generate", data=payload,
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return str(json.loads(response.read()).get("response", ""))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise OllamaUnavailableError(f"Ollama unavailable at {self.endpoint}: {exc}") from exc

    def runtime_info(self) -> dict[str, str]:
        return {"name": "ollama", "endpoint": self.endpoint, "model": self.model}
