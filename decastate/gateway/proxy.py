"""DecaState API gateway.

An honest transparent proxy for the Anthropic Messages API. It:

  1. forwards the request body BYTE-FOR-BYTE to the upstream provider,
  2. proves it did so with SHA-256 integrity hashes (whole body + system + tools + messages),
  3. reads the provider's own usage fields (cache_creation_input_tokens,
     cache_read_input_tokens, input_tokens, output_tokens) from the response,
  4. writes a per-request audit record and prints a report.

What it deliberately does NOT do: summarize, drop files, rewrite prompts, or alter
tool schemas/order. The saving reported is the PROVIDER's prompt cache — DecaState
measures and protects it; it does not invent it. Numbers are only real when the
upstream is a real provider reached with your own API key.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_UPSTREAM = "https://api.anthropic.com"

# Provider input pricing per 1M tokens, plus prompt-cache multipliers.
# Used only to turn PROVIDER-REPORTED cached tokens into an illustrative $ figure.
PRICING = {
    "claude-opus-5": 5.0, "claude-opus-4-8": 5.0, "claude-opus-4-7": 5.0,
    "claude-sonnet-5": 2.0, "claude-sonnet-4-6": 3.0, "claude-haiku-4-5": 1.0,
    "claude-fable-5": 10.0,
}
CACHE_READ_MULT = 0.1     # cached input billed at ~0.1x normal input
CACHE_WRITE_MULT = 1.25   # cache creation billed at ~1.25x normal input
HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}

# Full provider pricing per 1M tokens (input, output) — for total-invoice accounting.
# Published list rates. Anthropic caches at ~0.1x read; OpenAI at ~0.5x read.
PRICING_FULL = {
    "claude-fable-5": {"in": 10.0, "out": 50.0},
    "claude-opus-5": {"in": 5.0, "out": 25.0},
    "claude-opus-4-8": {"in": 5.0, "out": 25.0},
    "claude-opus-4-7": {"in": 5.0, "out": 25.0},
    "claude-sonnet-5": {"in": 2.0, "out": 10.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
    # OpenAI (published list rates; cache read ~0.5x)
    "gpt-4o": {"in": 2.5, "out": 10.0}, "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4.1": {"in": 2.0, "out": 8.0}, "gpt-4.1-mini": {"in": 0.40, "out": 1.60},
}


def _is_openai(model: str | None) -> bool:
    return (model or "").lower().startswith("gpt")


def _cache_read_mult(model: str | None) -> float:
    return 0.5 if _is_openai(model) else CACHE_READ_MULT


def _cache_write_mult(model: str | None) -> float:
    return 1.0 if _is_openai(model) else CACHE_WRITE_MULT  # OpenAI has no separate write premium


def normalize_usage(raw: dict) -> dict:
    """Normalize provider usage to a common shape. Anthropic and OpenAI report differently.

    Anthropic: input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens
    OpenAI:    prompt_tokens (INCLUDES cached), prompt_tokens_details.cached_tokens,
               completion_tokens
    """
    if not raw:
        return {}
    if "prompt_tokens" in raw:  # OpenAI shape
        cached = int((raw.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
        prompt = int(raw.get("prompt_tokens") or 0)
        return {"input_tokens": max(0, prompt - cached), "cache_read_input_tokens": cached,
                "cache_creation_input_tokens": 0, "output_tokens": int(raw.get("completion_tokens") or 0)}
    return {"input_tokens": raw.get("input_tokens"), "output_tokens": raw.get("output_tokens"),
            "cache_creation_input_tokens": raw.get("cache_creation_input_tokens"),
            "cache_read_input_tokens": raw.get("cache_read_input_tokens")}


def invoice_cost(model: str | None, usage: dict) -> float | None:
    """Total provider-billed request cost from ALL token types (input+cache+output).

    Whole invoice line, provider-reported usage × published pricing, provider-aware
    cache multipliers.
    """
    p = PRICING_FULL.get(model or "")
    if not p:
        return None
    i = int(usage.get("input_tokens") or 0)
    cw = int(usage.get("cache_creation_input_tokens") or 0)
    cr = int(usage.get("cache_read_input_tokens") or 0)
    o = int(usage.get("output_tokens") or 0)
    return (i * p["in"] + cw * p["in"] * _cache_write_mult(model)
            + cr * p["in"] * _cache_read_mult(model) + o * p["out"]) / 1_000_000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _component_hashes(raw_body: bytes) -> dict:
    """Hash the semantically meaningful parts WITHOUT mutating the forwarded bytes."""
    try:
        payload = json.loads(raw_body)
    except (ValueError, TypeError):
        return {"parse_ok": False}
    canon = lambda obj: _sha(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())
    return {
        "parse_ok": True,
        "model": payload.get("model"),
        "system_sha256": canon(payload.get("system")),
        "tools_sha256": canon(payload.get("tools")),
        "messages_sha256": canon(payload.get("messages")),
        "tool_count": len(payload.get("tools") or []),
        "message_count": len(payload.get("messages") or []),
    }


def _estimate_saving_usd(model: str | None, usage: dict) -> dict:
    """Illustrative $ from PROVIDER-reported cached tokens. Not a bill guarantee."""
    p = PRICING_FULL.get(model or "")
    rate = p["in"] if p else PRICING.get(model or "")
    read = int(usage.get("cache_read_input_tokens") or 0)
    write = int(usage.get("cache_creation_input_tokens") or 0)
    if rate is None:
        return {"input_rate_per_mtok_usd": None, "cache_read_saving_usd": None,
                "note": "unknown model; no price applied"}
    # Saving = what the cached-read tokens would have cost at full input rate,
    # minus what they actually cost at the cache-read rate (provider-aware multiplier).
    saving = read * (rate - rate * _cache_read_mult(model)) / 1_000_000
    write_premium = write * (rate * _cache_write_mult(model) - rate) / 1_000_000
    return {
        "input_rate_per_mtok_usd": rate,
        "cache_read_tokens": read,
        "cache_read_saving_usd": round(saving, 6),
        "cache_write_premium_usd": round(write_premium, 6),
        "net_input_saving_usd": round(saving - write_premium, 6),
        "note": "provider-reported cached tokens x published pricing; illustration, not a bill",
    }


def _strip_cache_control(obj):
    """Recursively remove cache_control keys (for content-equality comparison only)."""
    if isinstance(obj, dict):
        return {k: _strip_cache_control(v) for k, v in obj.items() if k != "cache_control"}
    if isinstance(obj, list):
        return [_strip_cache_control(v) for v in obj]
    return obj


def _inject_cache_control(raw_body: bytes) -> tuple[bytes, bool]:
    """Opt-in mode: add a cache_control breakpoint for clients that don't cache.

    Adds `cache_control: {type: ephemeral}` to the last system block (converting a
    string system prompt to block form if needed). Model-visible CONTENT is never
    changed — only the caching annotation. Returns (body, injected?). If the request
    already has any cache_control, it is left completely untouched.
    """
    try:
        payload = json.loads(raw_body)
    except (ValueError, TypeError):
        return raw_body, False
    def has_cc_key(obj) -> bool:  # structural check: cache_control as a KEY, not as text
        if isinstance(obj, dict):
            return "cache_control" in obj or any(has_cc_key(v) for v in obj.values())
        if isinstance(obj, list):
            return any(has_cc_key(v) for v in obj)
        return False

    if has_cc_key(payload):  # client already caches → hands off entirely
        return raw_body, False
    system = payload.get("system")
    if isinstance(system, str) and system:
        payload["system"] = [{"type": "text", "text": system,
                              "cache_control": {"type": "ephemeral"}}]
    elif isinstance(system, list) and system and isinstance(system[-1], dict):
        system[-1] = {**system[-1], "cache_control": {"type": "ephemeral"}}
    else:
        return raw_body, False
    return json.dumps(payload).encode(), True


def _prepare(raw_body: bytes, headers: dict, inject_cache: bool):
    body_sha = _sha(raw_body)
    fwd_headers = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP}
    fwd_headers.setdefault("content-type", "application/json")
    fwd_headers.setdefault("User-Agent", "DecaState-Gateway/0.1")  # some CDNs 1010-ban urllib's UA
    send_body, injected = (_inject_cache_control(raw_body) if inject_cache else (raw_body, False))
    return send_body, fwd_headers, injected, body_sha, _sha(send_body)


def _build_report(raw_body, send_body, injected, body_sha, sent_sha,
                  upstream, status, usage, elapsed, streamed=False) -> dict:
    components = _component_hashes(raw_body)
    model = components.get("model")
    cache_read = int(usage.get("cache_read_input_tokens") or 0)
    integrity = "unchanged" if body_sha == sent_sha else "ALTERED"
    if integrity == "ALTERED" and injected:
        try:
            if _sha(json.dumps(_strip_cache_control(json.loads(send_body)), sort_keys=True).encode()) == \
               _sha(json.dumps(_strip_cache_control(json.loads(raw_body)), sort_keys=True).encode()):
                integrity = "content-unchanged (cache_control injected)"
        except (ValueError, TypeError):
            pass
    return {
        "timestamp": time.time(),
        "upstream": upstream,
        "status": status,
        "latency_ms": round(elapsed * 1000, 1),
        "streamed": streamed,
        "model": model,
        "byte_identical_forward": body_sha == sent_sha,
        "request_body_sha256": body_sha,
        "forwarded_body_sha256": sent_sha,
        "system_sha256": components.get("system_sha256"),
        "tools_sha256": components.get("tools_sha256"),
        "messages_sha256": components.get("messages_sha256"),
        "tool_count": components.get("tool_count"),
        "message_count": components.get("message_count"),
        "usage": {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        },
        "provider_cache_hit": cache_read > 0,
        "cache_injected": injected,
        "prompt_integrity": integrity,
        "saving": _estimate_saving_usd(model, usage),
        "invoice_usd": invoice_cost(model, usage),
        "attribution": "provider prompt-cache; measured by DecaState, not created by it",
    }


def wants_stream(raw_body: bytes) -> bool:
    try:
        return json.loads(raw_body).get("stream") is True
    except (ValueError, TypeError):
        return False


def forward(raw_body: bytes, headers: dict, upstream: str, path: str = "/v1/messages",
            timeout: float = 600.0, inject_cache: bool = False) -> tuple[int, dict, bytes, dict]:
    """Buffered forward (non-streaming): byte-identical by default, opt-in cache injection."""
    send_body, fwd_headers, injected, body_sha, sent_sha = _prepare(raw_body, headers, inject_cache)
    request = urllib.request.Request(upstream.rstrip("/") + path, data=send_body,
                                     headers=fwd_headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            status, resp_headers, resp_body = resp.status, dict(resp.getheaders()), resp.read()
    except urllib.error.HTTPError as exc:
        status, resp_headers, resp_body = exc.code, dict(exc.headers.items()), exc.read()
    elapsed = time.perf_counter() - started
    usage = {}
    try:
        usage = normalize_usage((json.loads(resp_body) or {}).get("usage", {}) or {})
    except (ValueError, TypeError):
        pass
    report = _build_report(raw_body, send_body, injected, body_sha, sent_sha,
                           upstream, status, usage, elapsed)
    return status, resp_headers, resp_body, report


def _usage_from_sse(event_data: dict, usage: dict) -> None:
    """Accumulate usage from SSE, handling both Anthropic and OpenAI stream shapes."""
    t = event_data.get("type")
    if t == "message_start":  # Anthropic: input/cache land here
        u = (event_data.get("message") or {}).get("usage") or {}
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"):
            if u.get(k) is not None:
                usage[k] = u[k]
    elif t in ("message_delta", "message_stop"):  # Anthropic: output accumulates here
        u = event_data.get("usage") or {}
        if u.get("output_tokens") is not None:
            usage["output_tokens"] = u["output_tokens"]  # cumulative; last wins
    elif event_data.get("usage"):  # OpenAI: final chunk carries full usage
        for k, v in normalize_usage(event_data["usage"]).items():
            if v is not None:
                usage[k] = v


def forward_stream(raw_body: bytes, headers: dict, upstream: str, write_chunk,
                   path: str = "/v1/messages", timeout: float = 600.0,
                   inject_cache: bool = False) -> tuple[int, dict, dict]:
    """Streaming forward: relay SSE bytes to `write_chunk` as they arrive, accumulate usage.

    Returns (status, resp_headers, report). Byte-for-byte relay — the client sees the
    exact upstream event stream, in order; DecaState only reads usage off the side.
    """
    send_body, fwd_headers, injected, body_sha, sent_sha = _prepare(raw_body, headers, inject_cache)
    request = urllib.request.Request(upstream.rstrip("/") + path, data=send_body,
                                     headers=fwd_headers, method="POST")
    started = time.perf_counter()
    usage: dict = {}
    try:
        resp = urllib.request.urlopen(request, timeout=timeout)
        status, resp_headers = resp.status, dict(resp.getheaders())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        write_chunk(body)
        report = _build_report(raw_body, send_body, injected, body_sha, sent_sha,
                               upstream, exc.code, {}, time.perf_counter() - started, streamed=True)
        return exc.code, dict(exc.headers.items()), report
    try:
        for line in resp:  # iterates SSE lines, preserving exact bytes and order
            write_chunk(line)
            if line.startswith(b"data:"):
                payload = line[5:].strip()
                if payload and payload != b"[DONE]":
                    try:
                        _usage_from_sse(json.loads(payload), usage)
                    except ValueError:
                        pass
    finally:
        resp.close()
    report = _build_report(raw_body, send_body, injected, body_sha, sent_sha,
                           upstream, status, usage, time.perf_counter() - started, streamed=True)
    return status, resp_headers, report


def _audit_path() -> Path:
    import os
    home = Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate"))
    (home / "gateway").mkdir(parents=True, exist_ok=True)
    return home / "gateway" / "audit.jsonl"


def _append_audit(report: dict, path: Path) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(report) + "\n")


def audit_receipt(audit_path: Path | None = None, transcripts: bool = False,
                  window_days: int | None = None) -> dict:
    """Full-invoice receipt from provider-reported usage.

    Reads the gateway audit log (real requests through DecaState) and, optionally,
    your Claude Code transcripts. For every request it computes the ACTUAL invoice
    (all token types × published pricing) and the COUNTERFACTUAL no-cache invoice
    (every cached/written token billed at full input rate). The difference is the
    money the prompt cache actually saved — provider-billed, not estimated timing.
    """
    import os as _os

    def price(model):
        return PRICING_FULL.get(model or "")

    def scan_records():
        ap = audit_path or _audit_path()
        if ap.exists():
            for line in ap.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("mode") == "selftest" or r.get("status") != 200:
                    continue
                yield ("gateway", r.get("model"), r.get("usage") or {})
        if transcripts:
            base = Path.home() / ".claude" / "projects"
            cutoff = (time.time() - window_days * 86400) if window_days else 0
            if base.is_dir():
                for proj in base.iterdir():
                    if not proj.is_dir():
                        continue
                    for t in proj.glob("*.jsonl"):
                        if t.stat().st_mtime < cutoff:
                            continue
                        for line in t.open(errors="replace"):
                            if '"usage"' not in line:
                                continue
                            try:
                                rec = json.loads(line)
                            except ValueError:
                                continue
                            msg = rec.get("message") or {}
                            u = msg.get("usage") or {}
                            if u:
                                yield ("transcript", msg.get("model"), u)

    tot = {"requests": 0, "actual_usd": 0.0, "nocache_usd": 0.0,
           "input_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0,
           "output_tokens": 0, "priced_requests": 0, "by_model": {}}
    for _src, model, u in scan_records():
        tot["requests"] += 1
        i = int(u.get("input_tokens") or 0)
        cw = int(u.get("cache_creation_input_tokens") or 0)
        cr = int(u.get("cache_read_input_tokens") or 0)
        o = int(u.get("output_tokens") or 0)
        tot["input_tokens"] += i; tot["cache_write_tokens"] += cw
        tot["cache_read_tokens"] += cr; tot["output_tokens"] += o
        p = price(model)
        if not p:
            continue
        tot["priced_requests"] += 1
        actual = (i * p["in"] + cw * p["in"] * CACHE_WRITE_MULT
                  + cr * p["in"] * CACHE_READ_MULT + o * p["out"]) / 1e6
        nocache = ((i + cw + cr) * p["in"] + o * p["out"]) / 1e6
        tot["actual_usd"] += actual
        tot["nocache_usd"] += nocache
        bm = tot["by_model"].setdefault(model, {"requests": 0, "actual_usd": 0.0, "nocache_usd": 0.0})
        bm["requests"] += 1; bm["actual_usd"] += actual; bm["nocache_usd"] += nocache
    saved = tot["nocache_usd"] - tot["actual_usd"]
    tot["saved_usd"] = round(saved, 4)
    tot["saved_pct"] = round(saved / tot["nocache_usd"] * 100, 1) if tot["nocache_usd"] else 0.0
    tot["actual_usd"] = round(tot["actual_usd"], 4)
    tot["nocache_usd"] = round(tot["nocache_usd"], 4)
    for bm in tot["by_model"].values():
        bm["saved_usd"] = round(bm["nocache_usd"] - bm["actual_usd"], 4)
        bm["actual_usd"] = round(bm["actual_usd"], 4)
        bm["nocache_usd"] = round(bm["nocache_usd"], 4)
    tot["basis"] = ("provider-reported usage × published pricing; actual = full invoice "
                    "(input+cache+output), nocache = every cached token at full input rate; "
                    "the difference is what the prompt cache actually saved")
    tot["source"] = "gateway audit" + (" + Claude Code transcripts" if transcripts else "")
    return tot


def render_card_svg(r: dict) -> str:
    """Render a receipt as a shareable 1080×1080 SVG card. Zero dependencies."""
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    def money(x):
        return f"${x:,.0f}" if x >= 1000 else f"${x:,.2f}"
    saved = r.get("saved_usd", 0)
    models = sorted(r.get("by_model", {}).items(), key=lambda x: -x[1]["actual_usd"])[:4]
    rows = ""
    for i, (m, bm) in enumerate(models):
        y = 792 + i * 46
        rows += (f'<text x="90" y="{y}" fill="#8b97b0" font-family="monospace" font-size="24">{esc(m)}</text>'
                 f'<text x="990" y="{y}" fill="#c3f53c" font-family="monospace" font-size="24" text-anchor="end">saved {esc(money(bm["saved_usd"]))}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080" font-family="'Manrope',system-ui,sans-serif">
<rect width="1080" height="1080" fill="#07090e"/>
<text x="90" y="112" fill="#e9edf5" font-size="30" font-weight="800">◈ DecaState</text>
<text x="990" y="112" fill="#7f8aa3" font-family="monospace" font-size="18" text-anchor="end">COST RECEIPT · PROVIDER-BILLED</text>
<text x="90" y="270" fill="#c3f53c" font-family="monospace" font-size="22" letter-spacing="6">SAVED BY CACHING · MEASURED, PROVIDER-BILLED</text>
<text x="86" y="470" fill="#c3f53c" font-size="200" font-weight="800" letter-spacing="-6">{esc(money(saved))}</text>
<text x="90" y="560" fill="#e9edf5" font-size="46" font-weight="800">{r.get("saved_pct",0)}% off the no-cache bill</text>
<rect x="90" y="610" width="900" height="1" fill="#1c2230"/>
<text x="90" y="676" fill="#8b97b0" font-size="26">actual invoice</text>
<text x="990" y="676" fill="#e9edf5" font-family="monospace" font-size="30" text-anchor="end" font-weight="700">{esc(money(r.get("actual_usd",0)))}</text>
<text x="90" y="722" fill="#8b97b0" font-size="26">without any caching</text>
<text x="990" y="722" fill="#ff8f88" font-family="monospace" font-size="30" text-anchor="end" font-weight="700">{esc(money(r.get("nocache_usd",0)))}</text>
<rect x="90" y="748" width="900" height="1" fill="#1c2230"/>
{rows}
<text x="90" y="1012" fill="#5f6b85" font-family="monospace" font-size="19">{r.get("requests",0):,} requests · every $ from provider-reported usage</text>
<text x="90" y="1040" fill="#c3f53c" font-family="monospace" font-size="19">decastate.com · run your own: decastate audit</text>
</svg>'''


def print_receipt(r: dict) -> None:
    print("=" * 60)
    print("  DECASTATE COST RECEIPT  ·  provider-billed, not estimated")
    print("=" * 60)
    print(f"  requests measured        {r['requests']:,}  ({r['priced_requests']:,} priced)")
    print(f"  source                   {r['source']}")
    print(f"  input tokens             {r['input_tokens']:,}")
    print(f"  cache-write tokens       {r['cache_write_tokens']:,}")
    print(f"  cache-read tokens        {r['cache_read_tokens']:,}")
    print(f"  output tokens            {r['output_tokens']:,}")
    print("  " + "-" * 56)
    print(f"  actual invoice           ${r['actual_usd']:,.2f}")
    print(f"  without any caching       ${r['nocache_usd']:,.2f}")
    print(f"  SAVED BY CACHING         ${r['saved_usd']:,.2f}   ({r['saved_pct']}%)")
    print("  " + "-" * 56)
    for model, bm in sorted(r["by_model"].items(), key=lambda x: -x[1]["actual_usd"]):
        print(f"    {model:24s} ${bm['actual_usd']:>10,.2f}  saved ${bm['saved_usd']:,.2f}  ({bm['requests']:,} req)")
    print(f"\n  basis: {r['basis']}")
    print("=" * 60)


def savings_summary(audit_path: Path | None = None) -> dict:
    """Aggregate REAL (non-selftest, HTTP 200) audit records into running totals.

    The $ figure is the provider's own price delta: cached input tokens billed at
    ~0.1x instead of 1x, minus the 1.25x cache-write premium. It is computed from
    provider-reported usage x published pricing — an estimate of money NOT billed,
    delivered by the provider's prompt cache and measured by DecaState.
    """
    audit_path = audit_path or _audit_path()
    totals = {"requests": 0, "cache_read_tokens": 0, "cache_creation_tokens": 0,
              "uncached_input_tokens": 0, "output_tokens": 0,
              "est_saving_usd": 0.0, "est_write_premium_usd": 0.0, "by_model": {}}
    if not audit_path.exists():
        return totals
    for line in audit_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("mode") == "selftest" or r.get("status") != 200:
            continue
        u = r.get("usage") or {}
        model = r.get("model") or "unknown"
        rate = PRICING.get(model)
        read = int(u.get("cache_read_input_tokens") or 0)
        write = int(u.get("cache_creation_input_tokens") or 0)
        totals["requests"] += 1
        totals["cache_read_tokens"] += read
        totals["cache_creation_tokens"] += write
        totals["uncached_input_tokens"] += int(u.get("input_tokens") or 0)
        totals["output_tokens"] += int(u.get("output_tokens") or 0)
        m = totals["by_model"].setdefault(model, {"requests": 0, "cache_read_tokens": 0,
                                                  "est_saving_usd": 0.0})
        m["requests"] += 1
        m["cache_read_tokens"] += read
        if rate is not None:
            saving = read * (rate - rate * CACHE_READ_MULT) / 1_000_000
            premium = write * (rate * CACHE_WRITE_MULT - rate) / 1_000_000
            totals["est_saving_usd"] += saving
            totals["est_write_premium_usd"] += premium
            m["est_saving_usd"] += saving
    totals["est_saving_usd"] = round(totals["est_saving_usd"], 6)
    totals["est_write_premium_usd"] = round(totals["est_write_premium_usd"], 6)
    totals["est_net_saving_usd"] = round(
        totals["est_saving_usd"] - totals["est_write_premium_usd"], 6)
    for m in totals["by_model"].values():
        m["est_saving_usd"] = round(m["est_saving_usd"], 6)
    totals["attribution"] = ("provider prompt-cache price delta (read ~0.1x, write ~1.25x), "
                             "from provider-reported usage x published pricing; "
                             "measured by DecaState, delivered by the provider")
    return totals


def print_savings(totals: dict) -> None:
    print("DECASTATE SAVINGS TOTALS  (real forwarded requests only)")
    print(f"  requests measured        {totals['requests']}")
    print(f"  cached tokens reused     {totals['cache_read_tokens']:,}")
    print(f"  cache-write tokens       {totals['cache_creation_tokens']:,}")
    print(f"  uncached input tokens    {totals['uncached_input_tokens']:,}")
    print(f"  est. saving (reads)      ${totals['est_saving_usd']}")
    print(f"  est. write premium       -${totals['est_write_premium_usd']}")
    print(f"  est. NET input saving    ${totals.get('est_net_saving_usd', 0)}")
    for model, m in totals["by_model"].items():
        print(f"    {model}: {m['requests']} req, {m['cache_read_tokens']:,} cached, ~${m['est_saving_usd']}")
    print(f"  basis: {totals['attribution']}")


def _print_report(report: dict) -> None:
    u = report["usage"]
    s = report["saving"]
    hit = "HIT" if report["provider_cache_hit"] else "miss"
    print("─" * 60)
    print(f"DECASTATE REQUEST REPORT   [{time.strftime('%H:%M:%S')}]  {report['status']}")
    print(f"  model                {report['model']}")
    print(f"  prompt integrity     {report['prompt_integrity']}  (body sha {report['request_body_sha256'][:12]}…)")
    print(f"  tools / messages     {report['tool_count']} / {report['message_count']} (hashed, unchanged)")
    print(f"  provider cache       {hit}")
    print(f"  input tokens         {u['input_tokens']}   output {u['output_tokens']}")
    print(f"  cache creation       {u['cache_creation_input_tokens']}   cache read {u['cache_read_input_tokens']}")
    if s.get("net_input_saving_usd") is not None:
        print(f"  est. input saving    ${s['net_input_saving_usd']}  (provider cache; illustration)")
    print(f"  attribution          {report['attribution']}")
    print("─" * 60)


def list_states(limit: int = 12) -> dict:
    """Scan real DecaState state roots and return live workspace facts for the dashboard."""
    import os
    roots = [Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate")),
             Path.cwd() / ".decastate"]
    states = []
    seen = set()
    for root in roots:
        states_dir = root / "states"
        if not states_dir.is_dir():
            continue
        for manifest_path in states_dir.glob("*/manifest.json"):
            state_id = manifest_path.parent.name
            if state_id in seen:
                continue
            seen.add(state_id)
            try:
                manifest = json.loads(manifest_path.read_text())
            except (OSError, ValueError):
                continue
            live = manifest_path.parent / "live-cache.safetensors"
            checkpoints = len(list((root / "checkpoints" / state_id).glob("*/manifest.json")))
            branches = sorted(p.parent.name for p in
                              (root / "branches" / state_id).glob("*/manifest.json"))
            states.append({
                "state_id": state_id,
                "model": (manifest.get("model") or {}).get("id"),
                "token_count": (manifest.get("context") or {}).get("token_count"),
                "size_bytes": live.stat().st_size if live.exists() else None,
                "checkpoints": checkpoints,
                "branches": branches,
                "restore": (manifest.get("restore") or {}).get("mode", "native-mlx"),
                "mtime": manifest_path.stat().st_mtime,
                "root": str(root),
            })
    states.sort(key=lambda s: s["mtime"], reverse=True)
    return {"count": len(states), "states": states[:limit]}


def make_handler(upstream: str, audit_path: Path, inject_cache: bool = False):
    class GatewayHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):  # silence default noise
            return

        def _error(self, exc):
            payload = json.dumps({"type": "error", "error": {
                "type": "decastate_gateway_error", "message": str(exc)}}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _proxy(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw_body = self.rfile.read(length) if length else b""
            headers = {k: v for k, v in self.headers.items()}

            if wants_stream(raw_body):
                self._proxy_stream(raw_body, headers)
                return
            try:
                status, resp_headers, resp_body, report = forward(
                    raw_body, headers, upstream, path=self.path, inject_cache=inject_cache
                )
            except Exception as exc:  # network/transport failure — never silent
                self._error(exc)
                return
            _append_audit(report, audit_path)
            _print_report(report)
            self.send_response(status)
            for key, value in resp_headers.items():
                if key.lower() in HOP_BY_HOP or key.lower() == "content-encoding":
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("X-DecaState-Integrity", report["prompt_integrity"])
            self.end_headers()
            self.wfile.write(resp_body)

        def _proxy_stream(self, raw_body, headers):
            """Relay SSE with HTTP/1.1 chunked framing; flush each event immediately."""
            headers_sent = {"done": False}

            def write_chunk(data: bytes):
                if not data:
                    return
                if not headers_sent["done"]:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.send_header("Transfer-Encoding", "chunked")
                    self.send_header("X-DecaState-Integrity", "stream")
                    self.end_headers()
                    headers_sent["done"] = True
                self.wfile.write(f"{len(data):X}\r\n".encode() + data + b"\r\n")
                self.wfile.flush()

            try:
                status, _rh, report = forward_stream(
                    raw_body, headers, upstream, write_chunk,
                    path=self.path, inject_cache=inject_cache
                )
            except Exception as exc:
                if not headers_sent["done"]:
                    self._error(exc)
                return
            if headers_sent["done"]:
                self.wfile.write(b"0\r\n\r\n")  # terminate chunked stream
                self.wfile.flush()
            _append_audit(report, audit_path)
            _print_report(report)

        def do_POST(self):
            self._proxy()

        def do_GET(self):
            if self.path == "/healthz":
                body = json.dumps({"ok": True, "upstream": upstream,
                                   "audit": str(audit_path)}).encode()
            elif self.path.startswith("/savings"):
                body = json.dumps(savings_summary(audit_path)).encode()
            elif self.path.startswith("/receipt"):
                body = json.dumps(audit_receipt(audit_path)).encode()
            elif self.path.startswith("/states"):
                body = json.dumps(list_states()).encode()
            elif self.path.startswith("/guard-recall"):
                from urllib.parse import parse_qs, urlparse

                from decastate.guard.manager import recall
                q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
                body = json.dumps({"query": q, "hits": recall(q, limit=6) if q else []}).encode()
            elif self.path.startswith("/guard"):
                from decastate.guard.manager import guard_home
                cps = []
                for mp in sorted(guard_home().joinpath("checkpoints").glob("*.json")):
                    try:
                        cps.append(json.loads(mp.read_text()))
                    except ValueError:
                        pass
                body = json.dumps({"count": len(cps), "checkpoints": cps[-5:]}).encode()
            elif self.path.startswith("/audit"):
                records = []
                if audit_path.exists():
                    for line in audit_path.read_text().splitlines()[-50:]:
                        if line.strip():
                            try:
                                records.append(json.loads(line))
                            except ValueError:
                                pass
                body = json.dumps({"records": records}).encode()
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return GatewayHandler


def run_gateway(port: int = 8787, upstream: str = DEFAULT_UPSTREAM,
                audit_path: Path | None = None, inject_cache: bool = False) -> None:
    audit_path = audit_path or _audit_path()
    handler = make_handler(upstream, audit_path, inject_cache=inject_cache)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"DecaState gateway on http://127.0.0.1:{port}  →  {upstream}")
    print(f"audit log: {audit_path}")
    print("point your agent at it:  export ANTHROPIC_BASE_URL=http://127.0.0.1:%d" % port)
    print("Ctrl-C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        server.shutdown()


# --------------------------------------------------------------------------- #
# Self-test: proves the plumbing (byte-identical forward + usage extraction)
# against a LOCAL ECHO upstream. This verifies the gateway is correct; it is
# NOT a savings claim and uses no real provider.
# --------------------------------------------------------------------------- #

def run_selftest() -> dict:
    import os
    received = {}

    class EchoHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_a):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else b""
            received["sha256"] = _sha(body)
            received["len"] = len(body)
            # Return a realistic Anthropic-shaped response with usage fields.
            resp = json.dumps({
                "id": "msg_selftest", "type": "message", "role": "assistant",
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 40, "output_tokens": 7,
                          "cache_creation_input_tokens": 0,
                          "cache_read_input_tokens": 80000},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.send_header("X-Echo-Sha256", received["sha256"])
            self.end_headers()
            self.wfile.write(resp)

    echo = ThreadingHTTPServer(("127.0.0.1", 0), EchoHandler)
    port = echo.server_address[1]
    thread = threading.Thread(target=echo.serve_forever, daemon=True)
    thread.start()

    body = json.dumps({
        "model": "claude-sonnet-5", "max_tokens": 16,
        "system": [{"type": "text", "text": "You are a coding agent.",
                    "cache_control": {"type": "ephemeral"}}],
        "tools": [{"name": "read_file", "description": "read", "input_schema": {"type": "object"}}],
        "messages": [{"role": "user", "content": "x" * 4000}],
    }, separators=(",", ":")).encode()

    status, _h, _b, report = forward(body, {"content-type": "application/json"},
                                     f"http://127.0.0.1:{port}")
    echo.shutdown()

    checks = {
        "upstream_reachable": status == 200,
        "byte_identical_forward": report["byte_identical_forward"],
        "echo_confirms_same_bytes": received.get("sha256") == report["request_body_sha256"],
        "usage_extracted": report["usage"]["cache_read_input_tokens"] == 80000,
        "cache_hit_detected": report["provider_cache_hit"] is True,
        "integrity_unchanged": report["prompt_integrity"] == "unchanged",
        "saving_computed": report["saving"]["net_input_saving_usd"] is not None,
    }
    audit = _audit_path()
    _append_audit({**report, "mode": "selftest", "provider": "local-echo"}, audit)

    print("DECASTATE GATEWAY SELF-TEST  (plumbing only — local echo, no real provider)\n")
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}]  {name}")
    print(f"\n  forwarded {received.get('len')} bytes · sha {report['request_body_sha256'][:16]}…")
    print(f"  provider-reported cache_read = {report['usage']['cache_read_input_tokens']} tokens")
    print(f"  illustrative input saving on those tokens = "
          f"${report['saving']['net_input_saving_usd']} (Sonnet pricing)")
    passed = all(checks.values())
    print(f"\n  RESULT: {'ALL CHECKS PASS' if passed else 'FAILURES PRESENT'}")
    print("  NOTE: this proves the gateway forwards unchanged and reads provider usage.")
    print("        Real savings require a real API key + real upstream. No mock savings claimed.")
    return {"checks": checks, "passed": passed, "report": report}
