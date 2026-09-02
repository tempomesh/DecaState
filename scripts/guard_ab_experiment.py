"""Pre-registered A/B: does Guard-style checkpoint+recall beat compaction-style
summarization for post-boundary factual fidelity — and at what token cost?

Design (controlled boundary experiment — honestly labeled: this simulates the
compaction boundary with real API calls and the REAL Guard code path; it does not
drive Claude Code's own end-to-end compaction, which is the follow-up study):

  Phase 1 "session log": ~15K tokens of REAL project content (benchmark JSONs,
  docs) containing exact ground-truth facts (numbers, hashes, timings).

  Boundary — three arms, all continuing to the SAME 10 exact-answer questions:
    A) COMPACTION-STYLE: a model writes a summary of the log (~800 tok cap);
       continuation context = summary only.               (mimics auto-compact)
    B) GUARD: the log is wrapped as a transcript, checkpointed by the REAL
       decastate.guard code; continuation context = resume brief + verbatim
       recall snippets for the question terms.            (our product)
    C) FULL-REPLAY reference: continuation context = the entire raw log.
       (upper bound on fidelity; the expensive thing both A and B avoid)

  Scoring: exact-substring match of ground truth in the answer (objective; no
  human judgment). 3 runs per arm. Provider-reported usage for every call.
  Results are published raw either way — including if A wins.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5"
RUNS = 3

# Ground truth is derived AT RUNTIME from the actual files in the log, so every
# question is answerable from the phase-1 content by construction.
def build_qa(root: Path) -> list[tuple[str, str]]:
    j = lambda rel: json.loads((root / rel).read_text())
    p1 = j("benchmarks/results/phase1_native_state.json")
    lc = j("benchmarks/results/long_context_resume.json")
    cr = j("benchmarks/results/checkpoint_rollback.json")
    fb = j("benchmarks/results/fork_baseline.json")
    cp = j("benchmarks/results/api_cache_proof.json")
    ss = j("benchmarks/results/api_session_savings.json")
    lc2048 = [r for r in lc["rows"] if r["context_tokens"] == 2048][0]
    lc1024 = [r for r in lc["rows"] if r["context_tokens"] == 1024][0]
    cr2048 = [r for r in cr["rows"] if r["context_tokens"] == 2048][0]
    coder = [b for b in fb["branches"] if b["branch"] == "coder"][0]
    return [
        ("What was the exact state_size_bytes in the phase1 native state result?", str(p1["state_size_bytes"])),
        ("What was the exact cold_prefill_seconds at 2048 context tokens in long_context_resume?", str(lc2048["cold_prefill_seconds"])),
        ("What was the exact resume_speedup at 1024 context tokens?", str(lc1024["resume_speedup"])),
        ("What was the exact coder branch fork_seconds in fork_baseline?", str(coder["fork_seconds"])),
        ("What is the coder branch native_state_sha256 (first 12 characters)?", coder["native_state_sha256"][:12]),
        ("What was the exact c1_creation_seconds at 2048 tokens in checkpoint_rollback?", str(cr2048["c1_creation_seconds"])),
        ("What was the direct_input_cost_usd in the api_session_savings result?", str(ss["direct_input_cost_usd"])),
        ("How many cache_read tokens did request 2 report in api_cache_proof (direct leg)?", str(cp["direct"]["req2"]["cache_read"])),
        ("What was the base_context_tokens in fork_baseline?", str(fb["base_context_tokens"])),
        ("What was the gateway_input_cost_usd in api_session_savings?", str(ss["gateway_input_cost_usd"])),
    ]

QA: list = []  # populated in main()

LOG_FILES = ["README.md", "DECASTATE_CODEX_COMPLETE_BUILD_PLAN.md",
             "marketing/API_SAVINGS_EXPLAINER.md", "docs/OPERATIONS.md",
             "benchmarks/results/phase1_native_state.json",
             "benchmarks/results/long_context_resume.json",
             "benchmarks/results/checkpoint_rollback.json",
             "benchmarks/results/fork_baseline.json",
             "benchmarks/results/api_cache_proof.json",
             "benchmarks/results/api_session_savings.json",
             "docs/GATEWAY.md", "docs/CONTEXT_GUARD.md"]


def call(messages: list, system: str | None = None, max_tokens: int = 900) -> dict:
    body = {"model": MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", "x-api-key": KEY,
                                          "anthropic-version": "2023-06-01",
                                          "User-Agent": "DecaState-GuardAB/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"API error {exc.code}: {exc.read().decode()[:200]}")


def text_of(resp: dict) -> str:
    return "\n".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")


def usage_of(resp: dict) -> dict:
    u = resp.get("usage", {})
    return {"in": u.get("input_tokens"), "out": u.get("output_tokens")}


def build_log() -> str:
    chunks = ["=== SESSION LOG: DecaState engineering session (real artifacts) ===\n"]
    for rel in LOG_FILES:
        p = ROOT / rel
        if p.is_file():
            chunks.append(f"\n--- {rel} ---\n{p.read_text(errors='replace')}\n")
    return "".join(chunks)


def guard_context(log: str) -> tuple[str, dict]:
    """Run the REAL guard pipeline on the log wrapped as a transcript (isolated home)."""
    import tempfile
    os.environ["DECASTATE_HOME"] = tempfile.mkdtemp(prefix="guard-ab-home-")

    from decastate.guard.manager import checkpoint, recall
    # wrap the log as transcript records (one user record per file chunk)
    # realistic record granularity: real Claude Code transcripts hold many small
    # records, not one giant blob — chunk to ~1200 chars on line boundaries.
    chunks, buf = [], []
    for line in log.splitlines(keepends=True):
        buf.append(line)
        if sum(len(x) for x in buf) > 1200:
            chunks.append("".join(buf)); buf = []
    if buf:
        chunks.append("".join(buf))
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        for i, chunk in enumerate(chunks):
            rec = {"type": "user", "timestamp": f"t{i}",
                   "message": {"role": "user", "content": chunk}}
            fh.write(json.dumps(rec) + "\n")
        tpath = Path(fh.name)
    manifest = checkpoint(tpath, session_id="guard-ab", trigger="experiment")
    brief = Path(manifest["paths"]["brief"]).read_text()
    # recall verbatim evidence for the question terms (the Guard workflow)
    snippets, seen = [], set()
    for q, _truth in QA:
        for h in recall(q, limit=2):
            key = (h["archive"], h.get("line"), h["text"][:60])
            if key in seen:
                continue
            seen.add(key)
            snippets.append(f"[recall · {h.get('ts','')}]\n{h['text'][:2600]}")
    ctx = brief + "\n\n=== VERBATIM EVIDENCE (guard-recall) ===\n" + "\n\n".join(snippets)
    return ctx, manifest["stats"]


def ask(context: str, label: str) -> tuple[str, dict]:
    questions = "\n".join(f"{i+1}. {q}" for i, (q, _t) in enumerate(QA))
    messages = [{"role": "user", "content":
                 f"{context}\n\n=== TASK ===\nAnswer each question with the exact value from the "
                 f"session materials above. If the exact value is not present, say UNKNOWN.\n{questions}"}]
    resp = call(messages)
    return text_of(resp), usage_of(resp)


def score(answer: str) -> int:
    return sum(1 for _q, truth in QA if truth.lower() in answer.lower())


def main() -> None:
    if not KEY:
        print("ANTHROPIC_API_KEY not set"); sys.exit(1)
    QA.extend(build_qa(ROOT))
    log = build_log()
    print(f"phase-1 log: ~{len(log)//4:,} tokens of real project content · {len(QA)} exact-answer questions · {RUNS} runs/arm\n")

    # Arm A summary (one per run — the 'compaction' the continuation depends on)
    results = {"A_compaction_summary": [], "B_guard": [], "C_full_replay": []}
    guard_ctx, guard_stats = guard_context(log)
    print(f"guard context built by real pipeline: {guard_stats['evidence_entries']} evidence entries, "
          f"context ~{len(guard_ctx)//4:,} tokens vs full log ~{len(log)//4:,}\n")

    for run in range(1, RUNS + 1):
        sm = call([{"role": "user", "content":
                    log + "\n\nContext is nearly full. Write a compaction summary of this session "
                          "(max ~800 tokens) preserving what matters for future work."}],
                  max_tokens=1000)
        summary = text_of(sm)
        a_ans, a_use = ask("=== COMPACTION SUMMARY OF EARLIER SESSION ===\n" + summary, "A")
        b_ans, b_use = ask(guard_ctx, "B")
        c_ans, c_use = ask(log, "C")
        row = {"run": run,
               "A": {"score": score(a_ans), "usage": a_use, "summary_usage": usage_of(sm)},
               "B": {"score": score(b_ans), "usage": b_use},
               "C": {"score": score(c_ans), "usage": c_use}}
        results["A_compaction_summary"].append(row["A"])
        results["B_guard"].append(row["B"])
        results["C_full_replay"].append(row["C"])
        print(f"run {run}:  A(compaction) {row['A']['score']}/10 @ {a_use['in']:,} in-tok   "
              f"B(guard) {row['B']['score']}/10 @ {b_use['in']:,} in-tok   "
              f"C(full) {row['C']['score']}/10 @ {c_use['in']:,} in-tok")
        time.sleep(1)

    def avg(arm, k="score"):
        return sum(r[k] for r in results[arm]) / RUNS
    def avg_in(arm):
        return sum(r["usage"]["in"] for r in results[arm]) / RUNS

    out = {"model": MODEL, "runs": RUNS, "questions": len(QA),
           "protocol": "controlled boundary experiment; real API calls, real guard pipeline; "
                       "does NOT drive Claude Code's own end-to-end compaction (follow-up study)",
           "accuracy": {"A_compaction": avg("A_compaction_summary"),
                        "B_guard": avg("B_guard"), "C_full_replay": avg("C_full_replay")},
           "avg_input_tokens": {"A_compaction": avg_in("A_compaction_summary"),
                                "B_guard": avg_in("B_guard"), "C_full_replay": avg_in("C_full_replay")},
           "raw": results, "qa": [{"q": q, "truth": t} for q, t in QA]}
    path = ROOT / "benchmarks/results/guard_ab.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nACCURACY  A(compaction)={out['accuracy']['A_compaction']:.1f}/10   "
          f"B(guard)={out['accuracy']['B_guard']:.1f}/10   C(full)={out['accuracy']['C_full_replay']:.1f}/10")
    print(f"IN-TOKENS A={out['avg_input_tokens']['A_compaction']:,.0f}   "
          f"B={out['avg_input_tokens']['B_guard']:,.0f}   C={out['avg_input_tokens']['C_full_replay']:,.0f}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
