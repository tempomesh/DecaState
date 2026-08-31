"""The big number, measured: input-cost saving over a REAL 10-request agent session.

Leg A: non-caching client, 10 requests direct to Anthropic (full price every time).
Leg B: same client, 10 requests through DecaState gateway --inject-cache.
Same ~13K-token repo prefix, 10 different instructions. All real billed requests.

Honest scope (printed in the output): applies to clients that don't already set
cache_control; requests must stay inside the provider cache TTL (~5 min, refreshed
per read); asymptote is 90% (Anthropic's own cache-read pricing).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GATEWAY = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8801")
MODEL, RATE = "claude-haiku-4-5", 1.0  # $/1M input

INSTRUCTIONS = [
    "Summarize the gateway in one line.",
    "Name one risk in state persistence.",
    "What does the checkpoint manager verify?",
    "Explain the fork model briefly.",
    "What is the integrity mechanism?",
    "Name the main CLI commands.",
    "What does 'wake' guarantee?",
    "Describe the storage layer in one line.",
    "What is NOT claimed by this project?",
    "Give one improvement suggestion.",
]


def post(base: str, instruction: str, context: str) -> dict:
    body = json.dumps({"model": MODEL, "max_tokens": 30, "system": context,
                       "messages": [{"role": "user", "content": instruction}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/messages", data=body, method="POST",
                                 headers={"content-type": "application/json", "x-api-key": KEY,
                                          "anthropic-version": "2023-06-01",
                                          "User-Agent": "DecaState-Proof/0.3"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"error": exc.code, "detail": exc.read().decode()[:200]}


def context_text() -> str:
    files = [ROOT / "README.md", ROOT / "decastate/gateway/proxy.py",
             ROOT / "decastate/checkpoint/manager.py", ROOT / "docs/GATEWAY.md"]
    chunks = ["You are a senior engineer reviewing the DecaState repository.\n"]
    for f in files:
        if f.is_file():
            chunks.append(f"\n===== {f.name} =====\n{f.read_text(errors='replace')}\n")
    return "".join(chunks)


def run_leg(label: str, base: str, context: str) -> dict:
    cost = 0.0
    reads = writes = full = 0
    for i, instruction in enumerate(INSTRUCTIONS, 1):
        r = post(base, instruction, context)
        if "error" in r:
            print(f"  [{label}] req{i} error {r['error']}: {r['detail']}")
            return {"ok": False}
        u = r.get("usage", {})
        fi, cw, cr = (u.get("input_tokens") or 0), (u.get("cache_creation_input_tokens") or 0), \
                     (u.get("cache_read_input_tokens") or 0)
        cost += (fi * RATE + cw * RATE * 1.25 + cr * RATE * 0.10) / 1e6
        full += fi; writes += cw; reads += cr
        print(f"  [{label}] req{i:2d}: input={fi:>6} write={cw:>6} read={cr:>6}")
        time.sleep(0.6)
    return {"ok": True, "input_cost_usd": round(cost, 6), "full_tokens": full,
            "write_tokens": writes, "read_tokens": reads}


def main() -> None:
    if not KEY:
        print("ANTHROPIC_API_KEY not set"); sys.exit(1)
    context = context_text()
    print(f"context: ~{len(context)//4} tokens · {len(INSTRUCTIONS)} requests per leg · {MODEL}\n")
    print("LEG A — non-caching client, DIRECT (full price every request)")
    a = run_leg("direct", "https://api.anthropic.com", context)
    print("\nLEG B — same client THROUGH DecaState --inject-cache")
    b = run_leg("gateway", GATEWAY, context)
    if not (a.get("ok") and b.get("ok")):
        sys.exit(1)
    saved = a["input_cost_usd"] - b["input_cost_usd"]
    pct = saved / a["input_cost_usd"] * 100
    result = {"model": MODEL, "requests_per_leg": len(INSTRUCTIONS),
              "direct_input_cost_usd": a["input_cost_usd"],
              "gateway_input_cost_usd": b["input_cost_usd"],
              "saved_usd": round(saved, 6), "saved_pct": round(pct, 1),
              "direct": a, "gateway": b,
              "honest_scope": ("non-caching Anthropic clients; same-prefix requests within "
                               "the ~5-min TTL (refreshed per read); asymptote 90% = "
                               "Anthropic's own cache-read pricing; provider-billed usage")}
    out = ROOT / "benchmarks/results/api_session_savings.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\n{'='*62}\nSESSION VERDICT ({len(INSTRUCTIONS)} requests, real bills):")
    print(f"  direct   ${a['input_cost_usd']:.6f}   (every request full price)")
    print(f"  gateway  ${b['input_cost_usd']:.6f}   (1 write + {len(INSTRUCTIONS)-1} cache reads)")
    print(f"  SAVED    ${saved:.6f}  =  {pct:.1f}% input-cost reduction")
    print(f"  scope: {result['honest_scope']}")
    print(f"  saved: {out}")


if __name__ == "__main__":
    main()
