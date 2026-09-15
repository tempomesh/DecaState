#!/usr/bin/env python3
"""E2E proof: the DecaState gateway measures a SELF-HOSTED model unchanged.

llama-server's OpenAI-compatible endpoint reports the same
``usage.prompt_tokens_details.cached_tokens`` field OpenAI uses, so the
gateway's existing OpenAI normalization measures self-hosted caching with
zero code changes:

  llama-server (any GGUF, your machine)
        ▲ byte-identical forward (SHA-256)
  DecaState gateway --upstream http://127.0.0.1:<llama-port>
        ▲ OpenAI-style /v1/chat/completions
  your app

Expected receipt on request 2 (same system prompt): cache_state=HIT with
reused tokens, and saving_state=**not_priced** — the honest answer for a
model with no per-token bill (the win is time/compute, not dollars, and
DecaState refuses to invent dollars).

Prereqs: llama-server running with a model, DecaState gateway running with
--upstream pointing at it. Writes
benchmarks/results/selfhosted_gateway_proof.json.

Usage:
  python3 scripts/selfhosted_gateway_proof.py \
      --gateway http://127.0.0.1:8790
"""
import argparse
import json
import os
import time
import urllib.request

SYS = ("You review the DecaState repo. "
       + " ".join(f"Module m{i} owner o{i}." for i in range(200)))


def post(url, body, timeout=180):
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:8790")
    ap.add_argument("--model", default="llama3.2")
    args = ap.parse_args()

    def chat(q):
        return post(args.gateway + "/v1/chat/completions", {
            "model": args.model, "max_tokens": 16, "temperature": 0,
            "cache_prompt": True,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": q}]})

    r1 = chat("who owns m4?")
    r2 = chat("who owns m11?")
    with urllib.request.urlopen(args.gateway + "/glass", timeout=5) as r:
        glass = json.loads(r.read())

    results = {
        "proof": "self-hosted model measured through the DecaState gateway, "
                 "no code changes",
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "request1_usage": r1.get("usage"),
        "request2_usage": r2.get("usage"),
        "glass_receipt": {k: glass.get(k) for k in (
            "model", "cache_state", "saving_state", "reused_tokens",
            "new_tokens", "generated_tokens", "prompt_integrity")},
        "assertions": {
            "req2_reused_cache": (r2.get("usage", {})
                                  .get("prompt_tokens_details", {})
                                  .get("cached_tokens", 0)) > 0,
            "cache_state_hit": glass.get("cache_state") == "HIT",
            "integrity_unchanged": glass.get("prompt_integrity") == "unchanged",
            "no_invented_dollars": glass.get("saving_state") == "not_priced",
        },
        "honesty": [
            "A self-hosted model has no per-token bill: the receipt shows "
            "reused tokens and refuses to price them (saving_state=not_priced).",
            "The real self-hosted win is prompt-phase time/compute — measured "
            "separately in llamacpp_state_proof.json.",
        ],
    }
    results["passed"] = all(results["assertions"].values())
    out = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results",
                       "selfhosted_gateway_proof.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(results["assertions"], indent=2))
    print("PASSED" if results["passed"] else "FAILED", "→", os.path.relpath(out))


if __name__ == "__main__":
    main()
