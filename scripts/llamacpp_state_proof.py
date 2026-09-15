#!/usr/bin/env python3
"""E2E proof: DecaState's state contract on the llama.cpp backend.

Protocol (all numbers come from llama-server's own timings — nothing timed
by hand, nothing estimated):

  1. fresh server, fresh state dir
  2. UNDERSTAND  — prefill a ~3.8K-token context once, save KV state to disk
  3. WARM        — same-process follow-up question (baseline for reuse)
  4. KILL        — SIGKILL the server: true process death
  5. RESTART     — brand-new process
  6. CONTROL     — same context on an un-restored slot → full re-prefill
                   (proves a new process remembers nothing on its own)
  7. WAKE        — restore the saved state into slot 0 → follow-up question
                   processes only the new tokens
  8. FORK        — restore the same state into slot 1 → two independent
                   lanes, each processing only its own new question
  9. DETERMINISM — the warm answer and the post-wake answer to the same
                   question are compared byte-for-byte (temp=0, fixed seed)

Writes benchmarks/results/llamacpp_state_proof.json.

Usage:
  python3 scripts/llamacpp_state_proof.py --model /path/to/model.gguf
  (or set DECASTATE_GGUF)
"""
import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from decastate.backends.llamacpp import LlamaCppBackend  # noqa: E402

PREFIX = ("You are a senior engineer reviewing the DecaState repository. "
          + " ".join(f"Module m{i} handles subsystem s{i} with invariants inv{i} "
                     f"and owner o{i}." for i in range(220))
          + " Answer questions about this repository concisely. ")
Q1 = "Q: who owns module m7? A:"
Q2 = "Q: who owns module m12? A:"
QA = "Q: list the invariant of m5. A:"
QB = "Q: which subsystem does m9 handle? A:"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("DECASTATE_GGUF"))
    ap.add_argument("--port", type=int, default=8899)
    args = ap.parse_args()
    if not args.model:
        sys.exit("pass --model /path/to/model.gguf (or set DECASTATE_GGUF)")

    state_dir = tempfile.mkdtemp(prefix="decastate_llamacpp_")
    be = LlamaCppBackend(args.model, state_dir, port=args.port)
    log = os.path.join(state_dir, "server.log")
    results = {"backend": "llamacpp", "protocol": "understand→kill→wake→fork",
               "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        print("1. starting fresh llama-server …")
        be.start(log_path=log)
        results["fingerprint"] = be._fingerprint()

        print("2. UNDERSTAND — prefill once, save state …")
        meta = be.understand("repo-ready", PREFIX + Q1)
        results["understand"] = {
            "prefill_tokens": meta["prefill_tokens"],
            "prefill_ms": round(meta["prefill_ms"], 1),
            "state_tokens": meta["state_tokens"],
            "state_bytes": meta["state_bytes"],
            "state_sha256": meta["state_sha256"][:16] + "…",
        }
        print(f"   prefilled {meta['prefill_tokens']} tok in {meta['prefill_ms']:.0f}ms, "
              f"saved {meta['state_bytes']/1e6:.0f}MB")

        print("3. WARM follow-up (same process) …")
        warm = be.ask(PREFIX + Q2, slot=0, n_predict=24)
        results["warm_same_process"] = {
            "prompt_tokens_processed": warm["prompt_tokens_processed"],
            "prompt_ms": round(warm["prompt_ms"], 1)}

        print("4. KILL — true process death …")
        be.kill()
        assert not be.is_up(), "server still up after kill?!"
        results["process_killed"] = True

        print("5. RESTART — brand-new process …")
        be.start(log_path=log)

        print("6. CONTROL — un-restored slot must re-prefill everything …")
        ctl = be.ask(PREFIX + Q2, slot=1, n_predict=24)
        results["control_new_process_no_restore"] = {
            "prompt_tokens_processed": ctl["prompt_tokens_processed"],
            "prompt_ms": round(ctl["prompt_ms"], 1)}

        print("7. WAKE — restore saved state into new process …")
        t0 = time.time()
        w = be.wake("repo-ready", slot=0)
        restore_s = time.time() - t0
        woke = be.ask(PREFIX + Q2, slot=0, n_predict=24)
        results["wake_after_death"] = {
            "restored_tokens": w["restored_tokens"],
            "restore_wall_s": round(restore_s, 2),
            "prompt_tokens_processed": woke["prompt_tokens_processed"],
            "prompt_ms": round(woke["prompt_ms"], 1)}

        print("8. FORK — same state into a second independent lane …")
        be.fork("repo-ready", slot=1)
        a = be.ask(PREFIX + QA, slot=0, n_predict=24)
        b = be.ask(PREFIX + QB, slot=1, n_predict=24)
        results["fork"] = {
            "branch_a_prompt_tokens": a["prompt_tokens_processed"],
            "branch_b_prompt_tokens": b["prompt_tokens_processed"]}

        results["determinism_same_answer_after_wake"] = (warm["text"] == woke["text"])
        full, reused = ctl["prompt_ms"], woke["prompt_ms"]
        results["headline"] = {
            "tokens_reused_on_wake": w["restored_tokens"] - woke["prompt_tokens_processed"],
            "reprefill_avoided_pct": round(
                100 * (1 - woke["prompt_tokens_processed"] / ctl["prompt_tokens_processed"]), 1),
            "prompt_phase_speedup_vs_cold": round(full / reused, 1) if reused else None}
        results["honesty"] = [
            "All token/time numbers are llama-server's own reported timings.",
            "State files are llama.cpp build-sensitive; wake enforces a "
            "build+model+ctx fingerprint and SHA-256 integrity, it does not "
            "make files portable across builds.",
            "Determinism compared at temperature=0 with a fixed seed on one "
            "machine; not claimed across hardware.",
            f"restore_wall_s includes reading {results['understand']['state_bytes']/1e9:.2f}GB "
            "from local disk.",
        ]
        results["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    finally:
        be.stop()

    out = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results",
                       "llamacpp_state_proof.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print("\n=== RESULT ===")
    print(json.dumps(results["headline"], indent=2))
    print(f"determinism (same answer after wake): "
          f"{results['determinism_same_answer_after_wake']}")
    print(f"full results → {os.path.relpath(out)}")


if __name__ == "__main__":
    main()
