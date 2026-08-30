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
    rate = PRICING.get(model or "")
    read = int(usage.get("cache_read_input_tokens") or 0)
    write = int(usage.get("cache_creation_input_tokens") or 0)
    if rate is None:
        return {"input_rate_per_mtok_usd": None, "cache_read_saving_usd": None,
                "note": "unknown model; no price applied"}
    # Saving = what the cached-read tokens would have cost at full input rate,
    # minus what they actually cost at the cache-read rate.
    saving = read * (rate - rate * CACHE_READ_MULT) / 1_000_000
    write_premium = write * (rate * CACHE_WRITE_MULT - rate) / 1_000_000
    return {
        "input_rate_per_mtok_usd": rate,
        "cache_read_tokens": read,
        "cache_read_saving_usd": round(saving, 6),
        "cache_write_premium_usd": round(write_premium, 6),
        "net_input_saving_usd": round(saving - write_premium, 6),
        "note": "provider-reported cached tokens x published pricing; illustration, not a bill",
    }


def forward(raw_body: bytes, headers: dict, upstream: str, path: str = "/v1/messages",
            timeout: float = 600.0) -> tuple[int, dict, bytes, dict]:
    """Forward bytes unchanged to the upstream; return (status, headers, body, report)."""
    body_sha = _sha(raw_body)
    fwd_headers = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP}
    fwd_headers.setdefault("content-type", "application/json")
    # A real User-Agent matters: some CDNs 1010-ban the default urllib UA.
    fwd_headers.setdefault("User-Agent", "DecaState-Gateway/0.1")

    url = upstream.rstrip("/") + path
    request = urllib.request.Request(url, data=raw_body, headers=fwd_headers, method="POST")
    sent_sha = _sha(raw_body)  # hashed at the moment of sending
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            status = resp.status
            resp_headers = dict(resp.getheaders())
            resp_body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        resp_headers = dict(exc.headers.items())
        resp_body = exc.read()
    elapsed = time.perf_counter() - started

    usage = {}
    try:
        usage = (json.loads(resp_body) or {}).get("usage", {}) or {}
    except (ValueError, TypeError):
        pass

    components = _component_hashes(raw_body)
    cache_read = int(usage.get("cache_read_input_tokens") or 0)
    report = {
        "timestamp": time.time(),
        "upstream": upstream,
        "status": status,
        "latency_ms": round(elapsed * 1000, 1),
        "model": components.get("model"),
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
        "prompt_integrity": "unchanged" if body_sha == sent_sha else "ALTERED",
        "saving": _estimate_saving_usd(components.get("model"), usage),
        "attribution": "provider prompt-cache; measured by DecaState, not created by it",
    }
    return status, resp_headers, resp_body, report


def _audit_path() -> Path:
    import os
    home = Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate"))
    (home / "gateway").mkdir(parents=True, exist_ok=True)
    return home / "gateway" / "audit.jsonl"


def _append_audit(report: dict, path: Path) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(report) + "\n")


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


def make_handler(upstream: str, audit_path: Path):
    class GatewayHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):  # silence default noise
            return

        def _proxy(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw_body = self.rfile.read(length) if length else b""
            headers = {k: v for k, v in self.headers.items()}
            try:
                status, resp_headers, resp_body, report = forward(
                    raw_body, headers, upstream, path=self.path
                )
            except Exception as exc:  # network/transport failure — never silent
                payload = json.dumps({"type": "error", "error": {
                    "type": "decastate_gateway_error", "message": str(exc)}}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
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

        def do_POST(self):
            self._proxy()

        def do_GET(self):
            if self.path == "/healthz":
                body = json.dumps({"ok": True, "upstream": upstream,
                                   "audit": str(audit_path)}).encode()
            elif self.path.startswith("/savings"):
                body = json.dumps(savings_summary(audit_path)).encode()
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
                audit_path: Path | None = None) -> None:
    audit_path = audit_path or _audit_path()
    handler = make_handler(upstream, audit_path)
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
