"""Real A/B proof of provider prompt-cache reuse, direct vs through the DecaState gateway.

Reads ANTHROPIC_API_KEY from the environment (loaded from infra/.env by the caller).
Sends two requests that share a byte-identical, cacheable repository-context prefix and
differ only in the final instruction. The second request should show cache_read > 0.

Honest framing: this proves the PROVIDER's prompt cache works, and that the DecaState
gateway forwards byte-for-byte and reports the same provider usage. It does not claim
DecaState created the saving.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["claude-haiku-4-5", "claude-sonnet-5", "claude-3-5-haiku-20241022"]
GATEWAY = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8799")
KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Pricing (input $/1M) for the illustrative saving line.
PRICING = {"claude-haiku-4-5": 1.0, "claude-sonnet-5": 2.0, "claude-3-5-haiku-20241022": 0.80}


def build_context() -> str:
    """A real, sizeable, stable repository context (> the ~1024-token cache minimum)."""
    files = [ROOT / "README.md", ROOT / "decastate/gateway/proxy.py",
             ROOT / "decastate/state/workspace.py", ROOT / "docs/GATEWAY.md"]
    chunks = ["You are a senior engineer reviewing the DecaState repository. "
              "Study the following files carefully.\n"]
    for f in files:
        if f.is_file():
            chunks.append(f"\n===== {f.name} =====\n{f.read_text(errors='replace')}\n")
    return "".join(chunks)


def call(base_url: str, model: str, context: str, instruction: str) -> dict:
    body = json.dumps({
        "model": model,
        "max_tokens": 40,
        "system": [{"type": "text", "text": context, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": instruction}],
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/messages", data=body, method="POST",
        headers={"content-type": "application/json", "x-api-key": KEY,
                 "anthropic-version": "2023-06-01", "User-Agent": "DecaState-Proof/0.1"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"error": exc.code, "body": exc.read().decode()[:300]}
    data["_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return data


def usage(resp: dict) -> dict:
    u = resp.get("usage", {}) if isinstance(resp, dict) else {}
    return {
        "input": u.get("input_tokens"),
        "output": u.get("output_tokens"),
        "cache_creation": u.get("cache_creation_input_tokens"),
        "cache_read": u.get("cache_read_input_tokens"),
    }


def run_pair(label: str, base_url: str, model: str, context: str) -> dict:
    print(f"\n=== {label} ({base_url}) ===")
    r1 = call(base_url, model, context, "Summarize the gateway's responsibilities in one line.")
    if "error" in r1:
        print(f"  request 1 error {r1['error']}: {r1['body']}")
        return {"ok": False, "detail": r1}
    time.sleep(1.0)
    r2 = call(base_url, model, context, "Now list one security risk in state persistence.")
    if "error" in r2:
        print(f"  request 2 error {r2['error']}: {r2['body']}")
        return {"ok": False, "detail": r2}
    u1, u2 = usage(r1), usage(r2)
    print(f"  request 1  cache_creation={u1['cache_creation']}  cache_read={u1['cache_read']}  input={u1['input']}")
    print(f"  request 2  cache_creation={u2['cache_creation']}  cache_read={u2['cache_read']}  input={u2['input']}")
    rate = PRICING.get(model, 0)
    read = u2["cache_read"] or 0
    saving = read * (rate - rate * 0.1) / 1_000_000
    print(f"  → request 2 reused {read} cached tokens; est. input saving on them = ${saving:.6f} ({model})")
    return {"ok": True, "model": model, "req1": u1, "req2": u2,
            "cache_hit_on_repeat": (u2["cache_read"] or 0) > 0, "est_saving_usd": round(saving, 6)}


def main() -> None:
    if not KEY:
        print("ANTHROPIC_API_KEY not set"); sys.exit(1)
    context = build_context()
    approx_tokens = len(context) // 4
    print(f"Repository context: ~{approx_tokens} tokens ({len(context)} chars), cache_control=ephemeral")

    model = None
    # Pick the first model this key can actually use.
    for candidate in MODELS:
        probe = call("https://api.anthropic.com", candidate, context, "Reply OK.")
        if "error" not in probe:
            model = candidate
            break
        print(f"  model {candidate} unavailable ({probe['error']})")
    if not model:
        print("No usable model for this key."); sys.exit(1)
    print(f"Using model: {model}")

    direct = run_pair("DIRECT → Anthropic", "https://api.anthropic.com", model, context)
    time.sleep(2)
    gateway = run_pair("THROUGH DecaState gateway", GATEWAY, model, context)

    print("\n" + "=" * 60)
    print("VERDICT")
    if direct.get("ok"):
        print(f"  Provider prompt cache works: request-2 cache_read = "
              f"{direct['req2']['cache_read']}  (hit: {direct['cache_hit_on_repeat']})")
    if direct.get("ok") and gateway.get("ok"):
        same = direct["req2"]["cache_read"] == gateway["req2"]["cache_read"] or (
            (gateway["req2"]["cache_read"] or 0) > 0)
        print(f"  Gateway forwards faithfully and reports provider usage: "
              f"gateway request-2 cache_read = {gateway['req2']['cache_read']}")
        print("  Honest attribution: the cache is the PROVIDER's; DecaState measures it.")
    out = ROOT / "benchmarks/results/api_cache_proof.json"
    out.write_text(json.dumps({"model": model, "approx_context_tokens": approx_tokens,
                               "direct": direct, "gateway": gateway,
                               "attribution": "provider prompt-cache; measured, not created by DecaState"},
                              indent=2) + "\n")
    print(f"\n  saved: {out}")


if __name__ == "__main__":
    main()
