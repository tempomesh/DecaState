"""DecaState Hub server — receives published receipts, serves the wall's data.

Design (production-lean, stdlib only, no dependencies):

  POST /api/receipts   accept an opt-in receipt from `decastate brag --publish`
  GET  /api/health     liveness + store stats

The server validates, rate-limits, dedupes, and appends to an on-disk JSONL
store, then atomically regenerates `<site_dir>/hub/data.json` — which the
static wall page fetches same-origin. LLM traffic NEVER flows through this
service; it only ever sees small receipt summaries users chose to publish.

Honesty is structural:
  - community entries are stored verified=false and labeled on the wall;
  - only seed entries from DecaState's own reproducible measurements carry
    verified=true;
  - numbers are clamped to sane bounds and the raw store is append-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 16 * 1024
MAX_ENTRIES_SERVED = 120
RATE_LIMIT = 10          # posts per IP per window
RATE_WINDOW = 3600       # seconds
HANDLE_RE = re.compile(r"^[A-Za-z0-9_\-]{2,24}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,24}$")
GOOGLE_CLIENT_ID = os.environ.get("DECASTATE_GOOGLE_CLIENT_ID", "")


def hub_home() -> Path:
    home = Path(os.environ.get("DECASTATE_HUB_HOME", Path.home() / "decastate-hub"))
    home.mkdir(parents=True, exist_ok=True)
    return home


def site_dir() -> Path:
    return Path(os.environ.get("DECASTATE_SITE_DIR", Path.home() / "decastate-site"))


def _store_path() -> Path:
    return hub_home() / "receipts.jsonl"


def _load_entries() -> list[dict]:
    path = _store_path()
    entries = []
    if path.exists():
        for line in path.open(errors="replace"):
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def _sanitize(payload: dict) -> dict | None:
    """Validate and clamp a submitted receipt. Returns None if rejected."""
    try:
        saved = float(payload.get("saved_usd"))
        pct = float(payload.get("saved_pct", 0))
        requests_n = int(payload.get("requests", 0))
    except (TypeError, ValueError):
        return None
    if not (0.0 <= saved <= 10_000_000) or not (0.0 <= pct <= 100.0) \
            or not (0 <= requests_n <= 100_000_000):
        return None
    handle = str(payload.get("handle") or "anonymous")
    if not HANDLE_RE.match(handle):
        handle = "anonymous"
    models = payload.get("top_models") or []
    if not isinstance(models, list):
        models = []
    models = [str(m)[:40] for m in models[:3]]
    source = str(payload.get("source") or "decastate audit")[:80]
    return {"handle": handle, "saved_usd": round(saved, 2), "saved_pct": round(pct, 1),
            "requests": requests_n, "top_models": models, "source": source,
            "verified": False, "kind": "community-reported"}


def _regenerate(entries: list[dict]) -> None:
    """Atomically rewrite the wall's data.json inside the static site."""
    out_dir = site_dir() / "hub"
    out_dir.mkdir(parents=True, exist_ok=True)
    verified = [e for e in entries if e.get("verified")]
    community = [e for e in entries if not e.get("verified")]
    data = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totals": {
            "combined_saved_usd": round(sum(e["saved_usd"] for e in entries), 2),
            "verified_saved_usd": round(sum(e["saved_usd"] for e in verified), 2),
            "community_saved_usd": round(sum(e["saved_usd"] for e in community), 2),
            "receipts": len(entries),
            "verified_receipts": len(verified),
        },
        "honesty": ("verified = DecaState's own reproducible measurements; "
                    "community = self-reported by users in reproducible format, "
                    "not independently verified"),
        "entries": sorted(entries, key=lambda e: e.get("ts", 0), reverse=True)[:MAX_ENTRIES_SERVED],
    }
    tmp = out_dir / ".data.json.tmp"
    tmp.write_text(json.dumps(data, indent=1))
    os.replace(tmp, out_dir / "data.json")


def _seed_if_empty() -> None:
    """First boot: import DecaState's own verified receipts from seed.json if present."""
    if _store_path().exists():
        return
    seed = hub_home() / "seed.json"
    if not seed.exists():
        _store_path().touch()
        _regenerate([])
        return
    try:
        seeds = json.loads(seed.read_text())
    except ValueError:
        seeds = []
    with _store_path().open("w") as fh:
        for s in seeds:
            s.setdefault("ts", time.time())
            s["verified"] = True
            s["kind"] = "verified (DecaState reproducible measurement)"
            s["id"] = hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()[:12]
            fh.write(json.dumps(s) + "\n")
    _regenerate(_load_entries())


def _append_line(name: str, obj: dict) -> None:
    with (hub_home() / name).open("a") as fh:
        fh.write(json.dumps(obj) + "\n")


def _verify_google_token(credential: str) -> dict | None:
    """Verify a Google ID token server-side via Google's tokeninfo endpoint."""
    import urllib.parse
    import urllib.request
    try:
        url = ("https://oauth2.googleapis.com/tokeninfo?id_token="
               + urllib.parse.quote(credential, safe=""))
        with urllib.request.urlopen(url, timeout=10) as resp:
            info = json.loads(resp.read())
    except Exception:
        return None
    if info.get("aud") != GOOGLE_CLIENT_ID:
        return None
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return None
    if not info.get("email"):
        return None
    return {"email": info["email"], "name": info.get("name", ""),
            "sub": info.get("sub", ""), "email_verified": info.get("email_verified")}


class HubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    _rate: dict = {}
    _sessions: dict = {}  # token -> user (in-memory; sessions reset on restart, fine for v0)

    def log_message(self, *_a):
        return

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _client_ip(self) -> str:
        return (self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or self.client_address[0])

    def do_GET(self):
        if self.path.startswith("/api/health"):
            entries = _load_entries()
            self._send(200, {"ok": True, "receipts": len(entries)})
        elif self.path.startswith("/api/auth/config"):
            self._send(200, {"google_client_id": GOOGLE_CLIENT_ID or None})
        elif self.path.startswith("/api/me"):
            token = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
            user = self._sessions.get(token)
            self._send(200, {"user": user} if user else {"user": None})
        else:
            self._send(404, {"error": "not found"})

    def _rate_ok(self, ip: str) -> bool:
        now = time.time()
        window = [t for t in self._rate.get(ip, []) if now - t < RATE_WINDOW]
        if len(window) >= RATE_LIMIT:
            return False
        self._rate[ip] = window + [now]
        return True

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_BODY:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except ValueError:
            return None

    def _handle_signup(self):
        if not self._rate_ok(self._client_ip()):
            self._send(429, {"error": "rate limited"})
            return
        payload = self._read_json()
        if payload is None:
            self._send(400, {"error": "invalid request"})
            return
        email = str(payload.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            self._send(400, {"error": "invalid email"})
            return
        eid = hashlib.sha256(email.encode()).hexdigest()[:16]
        existing = set()
        signups = hub_home() / "signups.jsonl"
        if signups.exists():
            for line in signups.open(errors="replace"):
                try:
                    existing.add(json.loads(line).get("id"))
                except ValueError:
                    pass
        if eid not in existing:
            _append_line("signups.jsonl", {
                "id": eid, "email": email, "ts": time.time(),
                "source": str(payload.get("source") or "site")[:40]})
        self._send(200, {"ok": True, "note": "you're on the list — launch updates only, never shared"})

    def _handle_google_auth(self):
        if not GOOGLE_CLIENT_ID:
            self._send(503, {"error": "google sign-in not configured yet"})
            return
        if not self._rate_ok(self._client_ip()):
            self._send(429, {"error": "rate limited"})
            return
        payload = self._read_json()
        credential = str((payload or {}).get("credential") or "")
        if not credential:
            self._send(400, {"error": "missing credential"})
            return
        user = _verify_google_token(credential)
        if user is None:
            self._send(401, {"error": "token verification failed"})
            return
        _append_line("users.jsonl", {**user, "ts": time.time()})
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        self._sessions[token] = {"email": user["email"], "name": user["name"]}
        self._send(200, {"ok": True, "token": token,
                         "user": {"email": user["email"], "name": user["name"]}})

    def do_POST(self):
        if self.path.startswith("/api/signup"):
            self._handle_signup()
            return
        if self.path.startswith("/api/auth/google"):
            self._handle_google_auth()
            return
        if not self.path.startswith("/api/receipts"):
            self._send(404, {"error": "not found"})
            return
        ip = self._client_ip()
        now = time.time()
        window = [t for t in self._rate.get(ip, []) if now - t < RATE_WINDOW]
        if len(window) >= RATE_LIMIT:
            self._send(429, {"error": "rate limited; try later"})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_BODY:
            self._send(413, {"error": "body size invalid"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            self._send(400, {"error": "invalid JSON"})
            return
        entry = _sanitize(payload)
        if entry is None:
            self._send(400, {"error": "receipt failed validation"})
            return
        entry["ts"] = now
        entry["id"] = hashlib.sha256(
            json.dumps({k: entry[k] for k in ("handle", "saved_usd", "requests", "source")},
                       sort_keys=True).encode()).hexdigest()[:12]
        entries = _load_entries()
        if any(e.get("id") == entry["id"] for e in entries):
            self._send(200, {"ok": True, "id": entry["id"], "note": "already published"})
            return
        with _store_path().open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
        self._rate[ip] = window + [now]
        _regenerate(entries + [entry])
        self._send(201, {"ok": True, "id": entry["id"],
                         "wall": "https://decastate.com/hub/",
                         "label": "community-reported (not independently verified)"})


def main() -> None:
    port = int(os.environ.get("DECASTATE_HUB_PORT", "8788"))
    _seed_if_empty()
    _regenerate(_load_entries())  # always refresh on boot
    server = ThreadingHTTPServer(("0.0.0.0", port), HubHandler)
    print(f"decastate-hub on :{port} · store={_store_path()} · site={site_dir()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
