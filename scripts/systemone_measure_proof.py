#!/usr/bin/env python3
"""Independent measurement: TypeSafe Jev (System One) vs an LLM, same workload.

TypeSafe's launch claims (~100x faster/cheaper, zero type errors) are their
own harness numbers. This script measures independently, the DecaState way:

  - one fixed decision workload: 12 support-ticket states x 3 questions each
    (route: Choice, urgency: Score, refund-eligible: Noul)
  - side A: Jev via POST https://api.typesafe.ai/v1/systemone
  - side B: an LLM asked to return the same decisions as strict JSON
  - measured per call: wall latency, provider-reported usage tokens,
    schema/parse failures (the "type error" count), reported confidence
  - cost is computed ONLY from explicitly passed prices, labeled as
    announced (Jev) or published (LLM) — never silently assumed
  - NOT measured here: decision quality/calibration (needs labeled data;
    recorded confidences are saved for a later scored pass)

Ready to fire the day early access lands:

  TYPESAFE_API_KEY=... ANTHROPIC_API_KEY=... \
      python3 scripts/systemone_measure_proof.py
  python3 scripts/systemone_measure_proof.py --dry-run   # no network

Writes benchmarks/results/systemone_measured.json.
"""
import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request

JEV_URL = "https://api.typesafe.ai/v1/systemone"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

TICKETS = [
    "Customer on the Pro plan reports checkout fails with a 502 after entering card details; happened 3 times in the last hour; they mention a demo to their own client tomorrow morning.",
    "User asks how to export their data to CSV; no error, just can't find the button; signed up two days ago on the free tier.",
    "Enterprise admin says SSO login loops back to the sign-in page for all 40 seats since this morning's release; escalation contact CC'd.",
    "Customer charged twice for the same monthly invoice, bank statement attached; polite tone; asks for one charge to be reversed.",
    "User reports the mobile app crashes on launch after the latest update; device is a 5-year-old Android; no purchase involved.",
    "Prospect asks whether the API supports webhooks and what the rate limits are; evaluating against a competitor this week.",
    "Customer says a feature they relied on (bulk archive) disappeared; they are on an annual plan renewed last week and threaten to cancel.",
    "User cannot reset password; reset email never arrives; checked spam; corporate mail domain.",
    "Customer reports numbers in the analytics dashboard differ from their own database export by about 4%; asks which is authoritative.",
    "Free-tier user asks for a refund for a subscription they say they never started; account shows a trial converted 6 months ago with no activity since.",
    "Customer praises support but asks to downgrade from Team to Starter at the next renewal; no urgency stated.",
    "User pasted an API key into a public forum post and asks what to do; key has production scopes.",
]

ROUTES = {
    "billing": "payments, invoices, refunds, plan changes",
    "technical": "bugs, crashes, errors, integrations",
    "security": "credentials, access, data exposure",
    "sales": "pre-sales questions, evaluations",
    "general": "how-to questions and everything else",
}
URGENCY = [
    "no time pressure; answer within days is fine",
    "normal queue; answer within one business day",
    "elevated; customer is blocked or money is involved",
    "urgent; production down, deadline hours away, or security exposure",
]

JEV_QUESTIONS = {
    "route": {"type": "choice",
              "instructions": "Which team should handle this ticket?",
              "criteria": ROUTES},
    "urgency": {"type": "score",
                "instructions": "How urgent is this ticket?",
                "criteria": URGENCY},
    "refund_eligible": {"type": "noul",
                        "instructions": "Is the customer plausibly owed a refund or credit?"},
}

LLM_PROMPT = (
    "You are a support-triage engine. Read the ticket and answer with STRICT "
    "JSON only, no prose, exactly this shape:\n"
    '{"route": one of ' + json.dumps(list(ROUTES)) + ', '
    '"urgency": integer 0-3 (0=' + URGENCY[0] + ' ... 3=' + URGENCY[3] + '), '
    '"refund_eligible_prob": number 0-1}\n\nTICKET: '
)


def _post(url, body, headers, timeout=120):
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", **headers})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data, (time.perf_counter() - t0) * 1000.0


def run_jev(key, model):
    calls, type_errors = [], 0
    for state in TICKETS:
        body = {"state": state, "model": model, "questions": JEV_QUESTIONS}
        data, ms = _post(JEV_URL, body, {"Authorization": f"Bearer {key}"})
        ans = data.get("answers", {})
        ok = (ans.get("route", {}).get("choice") in ROUTES
              and isinstance(ans.get("urgency", {}).get("score"), (int, float))
              and isinstance(ans.get("refund_eligible", {}).get("noul"), (int, float)))
        if not ok:
            type_errors += 1
        calls.append({"wall_ms": round(ms, 1), "usage": data.get("usage"),
                      "answers": ans, "schema_ok": ok})
    return calls, type_errors


def run_llm(key, model):
    calls, type_errors = [], 0
    for state in TICKETS:
        body = {"model": model, "max_tokens": 200,
                "messages": [{"role": "user", "content": LLM_PROMPT + state}]}
        data, ms = _post(ANTHROPIC_URL, body,
                         {"x-api-key": key, "anthropic-version": "2023-06-01"})
        text = "".join(b.get("text", "") for b in data.get("content", []))
        parsed, ok = None, False
        try:
            parsed = json.loads(text.strip().strip("`").lstrip("json"))
            ok = (parsed.get("route") in ROUTES
                  and isinstance(parsed.get("urgency"), int)
                  and isinstance(parsed.get("refund_eligible_prob"), (int, float)))
        except Exception:
            pass
        if not ok:
            type_errors += 1
        calls.append({"wall_ms": round(ms, 1), "usage": data.get("usage"),
                      "parsed": parsed, "schema_ok": ok})
    return calls, type_errors


def summarize(calls, in_price, out_price, in_key="input_tokens", out_key="output_tokens"):
    lat = [c["wall_ms"] for c in calls]
    tin = sum((c.get("usage") or {}).get(in_key) or 0 for c in calls)
    tout = sum((c.get("usage") or {}).get(out_key) or 0 for c in calls)
    cost = tin / 1e6 * in_price + tout / 1e6 * out_price
    return {"calls": len(calls), "latency_ms_median": round(statistics.median(lat), 1),
            "latency_ms_p95": round(sorted(lat)[max(0, int(len(lat) * .95) - 1)], 1),
            "input_tokens": tin, "output_tokens": tout,
            "cost_usd": round(cost, 6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev-model", default="jev-latest")
    ap.add_argument("--llm-model", default="claude-haiku-4-5")
    ap.add_argument("--jev-price-in", type=float, default=0.042,
                    help="$/MTok — TypeSafe ANNOUNCED pricing, unverified")
    ap.add_argument("--jev-price-out", type=float, default=0.0)
    ap.add_argument("--llm-price-in", type=float, default=1.0,
                    help="$/MTok — Anthropic published (haiku-4-5)")
    ap.add_argument("--llm-price-out", type=float, default=5.0)
    ap.add_argument("--dry-run", action="store_true",
                    help="build and validate both request shapes, no network")
    args = ap.parse_args()

    if args.dry_run:
        jev_body = {"state": TICKETS[0], "model": args.jev_model,
                    "questions": JEV_QUESTIONS}
        print("JEV request shape OK:", json.dumps(jev_body)[:120], "…")
        print("LLM prompt shape OK:", (LLM_PROMPT + TICKETS[0])[:120], "…")
        print("dry run passed — add TYPESAFE_API_KEY / ANTHROPIC_API_KEY to measure")
        return

    results = {"workload": f"{len(TICKETS)} tickets x 3 decisions",
               "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "honesty": [
                   "Latency includes our network path to each provider; "
                   "TypeSafe publishes West-Coast-measured numbers.",
                   "Jev cost uses ANNOUNCED early-access pricing "
                   f"(${args.jev_price_in}/MTok in) — verify on a real bill.",
                   "Decision QUALITY/calibration is not judged here; "
                   "confidences are recorded for a later scored pass.",
               ]}

    jkey, akey = os.environ.get("TYPESAFE_API_KEY"), os.environ.get("ANTHROPIC_API_KEY")
    if jkey:
        calls, terr = run_jev(jkey, args.jev_model)
        results["jev"] = summarize(calls, args.jev_price_in, args.jev_price_out)
        results["jev"]["type_errors"] = terr
        results["jev_calls"] = calls
    if akey:
        calls, terr = run_llm(akey, args.llm_model)
        results["llm"] = {"model": args.llm_model,
                          **summarize(calls, args.llm_price_in, args.llm_price_out)}
        results["llm"]["schema_or_parse_failures"] = terr
        results["llm_calls"] = calls
    if "jev" in results and "llm" in results and results["jev"]["cost_usd"]:
        results["measured_ratio"] = {
            "latency_median_x": round(results["llm"]["latency_ms_median"]
                                      / results["jev"]["latency_ms_median"], 1),
            "cost_x": round(results["llm"]["cost_usd"]
                            / results["jev"]["cost_usd"], 1)}
    if not (jkey or akey):
        raise SystemExit("set TYPESAFE_API_KEY and/or ANTHROPIC_API_KEY, "
                         "or use --dry-run")

    out = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results",
                       "systemone_measured.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({k: v for k, v in results.items()
                      if k in ("jev", "llm", "measured_ratio")}, indent=2))
    print("→", os.path.relpath(out))


if __name__ == "__main__":
    main()
