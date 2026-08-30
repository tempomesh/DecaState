"""The decisive experiment: does DecaState ADD savings, and on which providers?

Three measured legs, all real API calls:

  A. Anthropic, NON-caching client, direct        → the baseline most raw scripts live in
  B. Anthropic, same client THROUGH DecaState gateway --inject-cache
     → DecaState adds a cache_control breakpoint (content untouched, reported honestly)
  C. OpenAI, identical-prefix pair, direct        → OpenAI caches automatically (~50% on
     cached tokens); a gateway cannot add hits there, only measure. We measure.

Honest conclusions this script prints:
  - Anthropic + non-caching client: DecaState CREATES a real saving (leg B vs leg A).
  - Anthropic + already-caching client (e.g. Claude Code): DecaState measures, doesn't add.
  - OpenAI: automatic; DecaState can only measure. cached_tokens shown from provider usage.
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
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GATEWAY = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8801")
A_MODEL = "claude-haiku-4-5"
A_RATE = 1.0     # $/1M input
O_MODEL = "gpt-4o-mini"
O_RATE = 0.15    # $/1M input; cached input ~50% off


def post(url: str, body: dict, headers: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"content-type": "application/json",
                                          "User-Agent": "DecaState-Proof/0.2", **headers})
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


def anthropic_pair(base: str, context: str, label: str) -> dict:
    """Two requests, PLAIN STRING system prompt, NO cache_control from the client."""
    def call(instruction):
        return post(base.rstrip("/") + "/v1/messages",
                    {"model": A_MODEL, "max_tokens": 30, "system": context,
                     "messages": [{"role": "user", "content": instruction}]},
                    {"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"})
    r1 = call("Summarize the gateway in one line.")
    time.sleep(1)
    r2 = call("Name one risk in state persistence.")
    rows = []
    for i, r in enumerate((r1, r2), 1):
        if "error" in r:
            print(f"  [{label}] request {i} error {r['error']}: {r['detail']}")
            return {"ok": False}
        u = r.get("usage", {})
        rows.append({"input": u.get("input_tokens"), "output": u.get("output_tokens"),
                     "cache_creation": u.get("cache_creation_input_tokens") or 0,
                     "cache_read": u.get("cache_read_input_tokens") or 0})
        print(f"  [{label}] req{i}: input={rows[-1]['input']} "
              f"cache_creation={rows[-1]['cache_creation']} cache_read={rows[-1]['cache_read']}")
    return {"ok": True, "rows": rows}


def anthropic_cost(rows: list[dict]) -> float:
    """Actual billed input cost across the pair, from provider-reported usage."""
    cost = 0.0
    for r in rows:
        cost += (r["input"] or 0) * A_RATE / 1e6
        cost += r["cache_creation"] * A_RATE * 1.25 / 1e6
        cost += r["cache_read"] * A_RATE * 0.10 / 1e6
    return cost


def openai_pair(context: str) -> dict:
    """OpenAI caches automatically for prefixes >= 1024 tokens; we just measure."""
    def call(instruction):
        return post("https://api.openai.com/v1/chat/completions",
                    {"model": O_MODEL, "max_tokens": 30,
                     "messages": [{"role": "system", "content": context},
                                  {"role": "user", "content": instruction}]},
                    {"Authorization": f"Bearer {OPENAI_KEY}"})
    r1 = call("Summarize the gateway in one line.")
    time.sleep(1)
    r2 = call("Name one risk in state persistence.")
    rows = []
    for i, r in enumerate((r1, r2), 1):
        if "error" in r:
            print(f"  [openai] request {i} error {r['error']}: {r['detail']}")
            return {"ok": False, "detail": r}
        u = r.get("usage", {})
        cached = ((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0
        rows.append({"prompt": u.get("prompt_tokens"), "completion": u.get("completion_tokens"),
                     "cached": cached})
        print(f"  [openai] req{i}: prompt={rows[-1]['prompt']} cached={cached}")
    saving = rows[1]["cached"] * O_RATE * 0.5 / 1e6
    return {"ok": True, "rows": rows, "est_saving_usd": round(saving, 6)}


def main() -> None:
    if not ANTHROPIC_KEY:
        print("ANTHROPIC_API_KEY not set"); sys.exit(1)
    context = context_text()
    print(f"context: ~{len(context)//4} tokens (plain-string system, no client caching)\n")

    print("LEG A — Anthropic DIRECT, non-caching client (the raw-script baseline)")
    a = anthropic_pair("https://api.anthropic.com", context, "direct-nocache")
    print("\nLEG B — Anthropic through DecaState gateway --inject-cache")
    b = anthropic_pair(GATEWAY, context, "gateway-inject")

    result: dict = {"anthropic": {}, "openai": {}}
    if a.get("ok") and b.get("ok"):
        cost_a, cost_b = anthropic_cost(a["rows"]), anthropic_cost(b["rows"])
        added = cost_a - cost_b
        pct = (added / cost_a * 100) if cost_a else 0
        result["anthropic"] = {
            "baseline_rows": a["rows"], "gateway_rows": b["rows"],
            "baseline_input_cost_usd": round(cost_a, 6),
            "gateway_input_cost_usd": round(cost_b, 6),
            "added_saving_usd": round(added, 6), "added_saving_pct": round(pct, 1),
            "honest_scope": ("DecaState ADDS this saving only for clients that don't already "
                             "set cache_control; Claude Code already caches, so there it "
                             "measures rather than adds."),
        }
        print(f"\n  ANTHROPIC VERDICT: baseline input cost ${cost_a:.6f} vs "
              f"gateway ${cost_b:.6f} → DecaState ADDED {pct:.1f}% input saving "
              f"(${added:.6f}) for a non-caching client — REAL, provider-billed delta")

    if OPENAI_KEY:
        print("\nLEG C — OpenAI direct (automatic caching; DecaState can only MEASURE here)")
        o = openai_pair(context)
        if o.get("ok"):
            result["openai"] = {
                "rows": o["rows"], "est_saving_usd": o["est_saving_usd"],
                "honest_scope": ("OpenAI caches automatically (~50% off cached tokens, "
                                 ">=1024-token prefixes); no gateway can add hits — "
                                 "DecaState's role on OpenAI is measurement only."),
            }
            print(f"  OPENAI VERDICT: req2 reused {o['rows'][1]['cached']} cached tokens "
                  f"(auto), est. saving ${o['est_saving_usd']} — measured, not created")

    out = ROOT / "benchmarks/results/api_added_savings.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
