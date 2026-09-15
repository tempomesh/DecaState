"""DecaState backends — pluggable engines behind one state contract.

The contract every backend implements:

    understand(name, prompt)  -> process a context once, persist its KV state
    wake(name)                -> load that state into a FRESH process, no re-prefill
    fork(name, slot)          -> branch the same state into an independent lane
    ask(prompt, slot)         -> continue; reports how many tokens were processed

Backends:
    mlx       — Apple Silicon via mlx_lm (the original runtime; lives in
                decastate.runtime / decastate.state and is imported lazily
                by the CLI — not re-exported here to keep this package
                stdlib-only).
    llamacpp  — any OS / any GGUF model, driven over llama-server's HTTP
                slot save/restore API. Stdlib-only (urllib), no bindings.

Nothing in this package imports MLX or any third-party module.
"""

BACKENDS = {
    "llamacpp": "decastate.backends.llamacpp",
}
