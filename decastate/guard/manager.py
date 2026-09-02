"""Context Guard core: archive raw transcripts, build structured checkpoints,
and retrieve EXACT original evidence — never a lossy rewrite.

Design principles (the honest ones):
  1. NEVER summarize with a model. We archive verbatim and index verbatim.
     Anything we hand back later is the exact original bytes, with provenance.
  2. The raw transcript is the source of truth; the checkpoint is a map, not
     a replacement.
  3. Everything is local files under ~/.decastate/guard/. Nothing is uploaded.

What this deliberately does NOT claim: preventing compaction, touching the
provider's KV cache, or measuring subscription dollars.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

from decastate.utils.hashing import sha256_file

TEST_SIGNAL = re.compile(r"(\d+ (passed|failed))|((PASS|FAIL|OK|ERROR)\b)|(Tests?:? \d+)", re.I)
STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is",
             "it", "this", "that", "was", "are", "be", "as", "at", "by", "from", "we"}


def guard_home() -> Path:
    home = Path(os.environ.get("DECASTATE_HOME", Path.home() / ".decastate")) / "guard"
    (home / "archives").mkdir(parents=True, exist_ok=True)
    (home / "checkpoints").mkdir(parents=True, exist_ok=True)
    return home


def _iter_records(transcript: Path):
    for lineno, line in enumerate(transcript.open(errors="replace")):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            rec["_line"] = lineno
            yield rec
        except ValueError:
            continue


def _text_of(content) -> str:
    """Flatten Claude message content (string or block list) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    parts.append(_text_of(block.get("content")))
        return "\n".join(p for p in parts if p)
    return ""


def extract(transcript: Path) -> dict:
    """Walk a real Claude Code transcript and extract the structured facts."""
    user_msgs, assistant_msgs, files_touched, commands, test_signals = [], [], [], [], []
    evidence = []  # verbatim, indexed
    records = 0
    for rec in _iter_records(transcript):
        records += 1
        line_no = rec.get("_line", -1)
        rtype = rec.get("type")
        message = rec.get("message") or {}
        ts = rec.get("timestamp", "")
        if rtype == "user" and isinstance(message, dict):
            text = _text_of(message.get("content"))
            if text and not text.startswith(("<system-reminder", "[SYSTEM")):
                user_msgs.append({"ts": ts, "text": text[:2000]})
                evidence.append({"ts": ts, "line": line_no, "kind": "user", "text": text[:4000]})
        elif rtype == "assistant" and isinstance(message, dict):
            content = message.get("content")
            text = _text_of(content)
            if text:
                assistant_msgs.append({"ts": ts, "text": text[:2000]})
                evidence.append({"ts": ts, "line": line_no, "kind": "assistant", "text": text[:4000]})
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        tin = block.get("input") or {}
                        if name in ("Write", "Edit", "NotebookEdit") and tin.get("file_path"):
                            files_touched.append(tin["file_path"])
                            evidence.append({"ts": ts, "line": line_no, "kind": f"file:{name.lower()}",
                                             "path": tin["file_path"],
                                             "text": str(tin.get("content") or tin.get("new_string") or "")[:4000]})
                        elif name == "Bash" and tin.get("command"):
                            commands.append(tin["command"][:300])
                            evidence.append({"ts": ts, "line": line_no, "kind": "bash",
                                             "text": tin["command"][:4000]})
        # tool results ride on user-typed records in the transcript
        if isinstance(message, dict):
            raw = _text_of(message.get("content"))
            for line in raw.splitlines():
                if TEST_SIGNAL.search(line) and len(line) < 200:
                    test_signals.append({"ts": ts, "line": line.strip()})
    return {
        "records": records,
        "user_messages": user_msgs,
        "assistant_messages": assistant_msgs,
        "files_touched": sorted(set(files_touched)),
        "commands": commands,
        "test_signals": test_signals[-40:],
        "evidence": evidence,
    }


def checkpoint(transcript: Path, session_id: str | None = None, trigger: str = "manual") -> dict:
    """Archive the raw transcript + write a structured checkpoint + evidence index."""
    started = time.perf_counter()
    home = guard_home()
    session_id = session_id or transcript.stem
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = f"{session_id[:12]}-{stamp}"

    # 1. RAW ARCHIVE — the source of truth, hashed.
    archive_path = home / "archives" / f"{base}.jsonl"
    shutil.copy2(transcript, archive_path)
    archive_sha = sha256_file(archive_path)

    # 2. EXTRACT — verbatim facts, no model, no summarization.
    facts = extract(transcript)

    # 3. EVIDENCE INDEX — verbatim excerpts, searchable, provenance-stamped.
    index_path = home / "checkpoints" / f"{base}.evidence.jsonl"
    with index_path.open("w") as fh:
        for i, ev in enumerate(facts["evidence"]):
            fh.write(json.dumps({"id": i, "archive": archive_path.name, **ev}) + "\n")

    # 4. STRUCTURED CHECKPOINT — a map for resuming, pointing at exact evidence.
    manifest = {
        "guard_version": "0.1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "trigger": trigger,
        "session_id": session_id,
        "source_transcript": str(transcript),
        "raw_archive": {"file": archive_path.name, "bytes": archive_path.stat().st_size,
                        "sha256": archive_sha},
        "stats": {"records": facts["records"],
                  "user_messages": len(facts["user_messages"]),
                  "assistant_messages": len(facts["assistant_messages"]),
                  "files_touched": len(facts["files_touched"]),
                  "commands": len(facts["commands"]),
                  "evidence_entries": len(facts["evidence"])},
        "goals_first": [m["text"][:500] for m in facts["user_messages"][:3]],
        "goals_recent": [m["text"][:500] for m in facts["user_messages"][-5:]],
        "files_touched": facts["files_touched"],
        "recent_commands": facts["commands"][-15:],
        "test_signals": facts["test_signals"][-15:],
        "honesty": "raw archive is source of truth; this checkpoint is a map, not a summary; "
                   "recall returns exact original bytes with provenance",
        "seconds": round(time.perf_counter() - started, 3),
    }
    manifest_path = home / "checkpoints" / f"{base}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    # 5. RESUME BRIEF — small, paste-ready markdown for the fresh context.
    brief = [f"# Context Guard resume brief — {session_id[:12]} ({stamp})",
             f"Raw archive: {archive_path.name} · {manifest['raw_archive']['bytes']:,} bytes · "
             f"sha256 {archive_sha[:16]}…",
             "", "## Recent goals (verbatim, truncated)"]
    brief += [f"- {g[:300]}" for g in manifest["goals_recent"]]
    brief += ["", "## Files touched this session"]
    brief += [f"- {f}" for f in manifest["files_touched"][:40]]
    brief += ["", "## Last test signals"]
    brief += [f"- {t['line']}" for t in manifest["test_signals"]]
    brief += ["", f"Exact evidence on demand: `decastate guard-recall \"<query>\"` "
                  f"({manifest['stats']['evidence_entries']} indexed entries)"]
    (home / "checkpoints" / f"{base}.md").write_text("\n".join(brief) + "\n")
    manifest["paths"] = {"manifest": str(manifest_path), "brief": str(home / 'checkpoints' / f'{base}.md'),
                         "evidence_index": str(index_path), "archive": str(archive_path)}
    return manifest


def recall(query: str, limit: int = 5) -> list[dict]:
    """Search all evidence indexes; rare terms dominate (IDF-weighted), so a field
    name like 'cold_prefill_seconds' outweighs a common token like '2048'.
    Returns verbatim excerpts with provenance (use raw_record for exact bytes)."""
    import math
    home = guard_home()
    terms = [t for t in re.findall(r"[a-zA-Z0-9_./-]+", query.lower()) if t not in STOPWORDS]
    entries = []
    for index_path in sorted((home / "checkpoints").glob("*.evidence.jsonl")):
        for line in index_path.open(errors="replace"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            entries.append((ev, (ev.get("text", "") + " " + ev.get("path", "")).lower()))
    if not entries:
        return []
    n = len(entries)
    idf = {t: math.log(n / (1 + sum(1 for _e, hay in entries if t in hay))) + 0.1 for t in terms}
    hits = []
    for ev, hay in entries:
        score = sum(min(hay.count(t), 3) * idf[t] for t in terms)
        if query.lower() in hay:
            score += 10
        if score > 0:
            hits.append((round(score, 2), ev))
    hits.sort(key=lambda x: -x[0])
    return [{"score": s, **e} for s, e in hits[:limit]]


def raw_record_bytes(archive_name: str, line: int) -> bytes | None:
    """Return the EXACT original JSONL line as raw BYTES from the hashed archive.

    Binary mode end-to-end: no decoding, no replacement characters, no mangling.
    """
    path = guard_home() / "archives" / archive_name
    if not path.exists() or line < 0:
        return None
    with path.open("rb") as fh:
        for lineno, raw in enumerate(fh):
            if lineno == line:
                return raw.rstrip(b"\n")
    return None


def raw_record(archive_name: str, line: int) -> str | None:
    """Exact original JSONL line, decoded losslessly (surrogateescape round-trips)."""
    raw = raw_record_bytes(archive_name, line)
    return raw.decode("utf-8", errors="surrogateescape") if raw is not None else None


PRECOMPACT_HOOK = {
    "hooks": {
        "PreCompact": [{
            "matcher": "",
            "hooks": [{"type": "command",
                       "command": "decastate guard-precompact"}]
        }]
    }
}


def install_hook(settings_path: Path) -> dict:
    """Merge the PreCompact hook into a Claude Code settings.json (never clobbers)."""
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except ValueError as exc:
            raise RuntimeError(f"existing settings file is not valid JSON: {settings_path}") from exc
    hooks = settings.setdefault("hooks", {})
    entries = hooks.setdefault("PreCompact", [])
    if any("guard-precompact" in json.dumps(e) for e in entries):
        return {"installed": False, "reason": "already installed", "path": str(settings_path)}
    entries.append(PRECOMPACT_HOOK["hooks"]["PreCompact"][0])
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    return {"installed": True, "path": str(settings_path)}
