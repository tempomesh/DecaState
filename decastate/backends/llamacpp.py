"""llama.cpp backend — DecaState's state contract on any OS, any GGUF model.

Drives a local ``llama-server`` over HTTP (stdlib urllib only, no C bindings),
using its slot save/restore API as the persistence primitive:

    understand -> prefill once, save the slot's KV state to <name>.bin
    wake       -> restore <name>.bin into a slot of a brand-new process
    fork       -> restore the same .bin into a second slot (independent lane)

Every checkpoint gets a sidecar ``<name>.meta.json`` recording the server
build, model file identity, context size and a SHA-256 of the state file.
``wake`` refuses a checkpoint whose fingerprint doesn't match the running
server — the same wrong-model/corruption discipline as the MLX runtime.

Honest scope: state files are llama.cpp version-sensitive; the fingerprint
guard turns "silently wrong" into "explicit refusal", it does not make files
portable across llama.cpp builds.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

DEFAULT_PORT = 8899
DEFAULT_CTX = 8192
DEFAULT_SLOTS = 2


class LlamaCppError(RuntimeError):
    pass


class LlamaCppBackend:
    def __init__(self, model_path: str, state_dir: str, port: int = DEFAULT_PORT,
                 ctx: int = DEFAULT_CTX, slots: int = DEFAULT_SLOTS,
                 server_bin: str = "llama-server"):
        self.model_path = os.path.abspath(os.path.expanduser(model_path))
        self.state_dir = os.path.abspath(os.path.expanduser(state_dir))
        self.port = port
        self.ctx = ctx
        self.slots = slots
        self.server_bin = server_bin
        self.base = f"http://127.0.0.1:{port}"
        self.proc: subprocess.Popen | None = None
        os.makedirs(self.state_dir, exist_ok=True)

    # ---------- server lifecycle ----------
    def start(self, log_path: str | None = None, wait_s: int = 60) -> None:
        if self.is_up():
            return
        if not os.path.exists(self.model_path):
            raise LlamaCppError(f"model not found: {self.model_path}")
        log = open(log_path, "ab") if log_path else subprocess.DEVNULL
        self.proc = subprocess.Popen(
            [self.server_bin, "-m", self.model_path, "-c", str(self.ctx),
             "-np", str(self.slots), "--port", str(self.port),
             "--slot-save-path", self.state_dir],
            stdout=log, stderr=subprocess.STDOUT)
        for _ in range(wait_s):
            if self.is_up():
                return
            time.sleep(1)
        raise LlamaCppError(f"llama-server did not become healthy on :{self.port} "
                            f"within {wait_s}s")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def kill(self) -> None:
        """True process death — no graceful anything (used by the proof)."""
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=10)
        self.proc = None

    def is_up(self) -> bool:
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=2) as r:
                return b'"ok"' in r.read()
        except Exception:
            return False

    # ---------- http ----------
    def _post(self, path: str, body: dict, timeout: int = 300) -> dict:
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise LlamaCppError(f"{path} -> HTTP {e.code}: {e.read()[:200]!r}") from e

    def props(self) -> dict:
        with urllib.request.urlopen(self.base + "/props", timeout=5) as r:
            return json.loads(r.read())

    # ---------- fingerprint guard ----------
    def _fingerprint(self) -> dict:
        p = self.props()
        st = os.stat(self.model_path)
        return {
            "backend": "llamacpp",
            "server_build": p.get("build_info", "unknown"),
            "model_path": self.model_path,
            "model_bytes": st.st_size,
            "n_ctx_per_slot": self.ctx // max(1, self.slots),
        }

    # ---------- the state contract ----------
    def ask(self, prompt: str, slot: int = 0, n_predict: int = 64,
            temperature: float = 0.0, seed: int = 7) -> dict:
        r = self._post("/completion", {
            "prompt": prompt, "n_predict": n_predict, "temperature": temperature,
            "seed": seed, "cache_prompt": True, "id_slot": slot})
        t = r.get("timings", {})
        return {"text": r.get("content", ""),
                "prompt_tokens_processed": t.get("prompt_n"),
                "prompt_ms": t.get("prompt_ms"),
                "tokens_cached": r.get("tokens_cached")}

    def understand(self, name: str, prompt: str, slot: int = 0) -> dict:
        """Process a context once and persist the slot's KV state under `name`."""
        first = self.ask(prompt, slot=slot, n_predict=1)
        saved = self._post(f"/slots/{slot}?action=save", {"filename": f"{name}.bin"})
        bin_path = os.path.join(self.state_dir, f"{name}.bin")
        meta = {
            "name": name,
            "fingerprint": self._fingerprint(),
            "state_tokens": saved.get("n_saved"),
            "state_bytes": saved.get("n_written"),
            "state_sha256": _sha256_file(bin_path),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with open(os.path.join(self.state_dir, f"{name}.meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        meta["prefill_tokens"] = first["prompt_tokens_processed"]
        meta["prefill_ms"] = first["prompt_ms"]
        return meta

    def wake(self, name: str, slot: int = 0, verify_hash: bool = True) -> dict:
        """Restore a named state into (possibly) a brand-new process."""
        meta_path = os.path.join(self.state_dir, f"{name}.meta.json")
        bin_path = os.path.join(self.state_dir, f"{name}.bin")
        if not (os.path.exists(meta_path) and os.path.exists(bin_path)):
            raise LlamaCppError(f"no checkpoint named {name!r} in {self.state_dir}")
        with open(meta_path) as f:
            meta = json.load(f)
        want, have = meta["fingerprint"], self._fingerprint()
        for k in ("server_build", "model_bytes", "n_ctx_per_slot"):
            if want.get(k) != have.get(k):
                raise LlamaCppError(
                    f"fingerprint mismatch on {k!r}: checkpoint={want.get(k)!r} "
                    f"server={have.get(k)!r} — refusing to wake a state into the "
                    f"wrong model/build/context.")
        if verify_hash and _sha256_file(bin_path) != meta["state_sha256"]:
            raise LlamaCppError(f"state file for {name!r} failed SHA-256 integrity check")
        r = self._post(f"/slots/{slot}?action=restore", {"filename": f"{name}.bin"})
        return {"name": name, "slot": slot, "restored_tokens": r.get("n_restored")}

    def fork(self, name: str, slot: int) -> dict:
        """Branch a named state into another slot — an independent lane."""
        return self.wake(name, slot=slot)

    def list_states(self) -> list[dict]:
        out = []
        for fn in sorted(os.listdir(self.state_dir)):
            if fn.endswith(".meta.json"):
                with open(os.path.join(self.state_dir, fn)) as f:
                    out.append(json.load(f))
        return out


def _sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
