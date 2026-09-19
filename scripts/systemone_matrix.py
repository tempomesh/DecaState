#!/usr/bin/env python3
"""Benchmark matrix: Jev vs the frontier lineup on the SAME 36 decisions.

Reuses the workload + runners from systemone_measure_proof.py and adds an
OpenAI provider path, so we can measure Jev against several models at once.

Design (keeps spend tiny and correct):
  - COST is token pricing → location-independent → run each model ONCE.
  - LATENCY is location-dependent → run this script in each region (SG, US).
  - Cost only computed from prices passed on the command line, each labeled
    (published for LLMs, announced for Jev).

Env: TYPESAFE_API_KEY, ANTHROPIC_API_KEY, and OPENAI_API_KEY (for Astra).

Examples:
  # Anthropic frontier + Jev, this location:
  python3 scripts/systemone_matrix.py \
      --anthropic claude-haiku-4-5:1:5 claude-sonnet-5:2:10 claude-fable-5:10:50
  # add an OpenAI model once you know the id + pricing:
  python3 scripts/systemone_matrix.py --openai gpt-6-astra:10:40
  --region SG   # label only; run the same script on the US box with --region US

Writes benchmarks/results/systemone_matrix_<REGION>.json
"""
import argparse, json, os, statistics, time, urllib.request, urllib.error, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.systemone_measure_proof import (  # noqa: E402
    TICKETS, JEV_QUESTIONS, LLM_PROMPT, ROUTES, run_jev, summarize)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _post(url, body, headers, timeout=180):
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", **headers})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), (time.perf_counter() - t0) * 1000.0


def run_anthropic(key, model):
    calls, terr = [], 0
    for s in TICKETS:
        try:
            data, ms = _post(ANTHROPIC_URL,
                {"model": model, "max_tokens": 200,
                 "messages": [{"role": "user", "content": LLM_PROMPT + s}]},
                {"x-api-key": key, "anthropic-version": "2023-06-01"})
        except urllib.error.HTTPError as e:
            return None, f"HTTP {e.code}: {e.read()[:120]!r}"
        text = "".join(b.get("text", "") for b in data.get("content", []))
        ok = _schema_ok(text)
        terr += 0 if ok else 1
        calls.append({"wall_ms": round(ms, 1), "usage": data.get("usage"), "schema_ok": ok})
    return calls, terr


def run_openai(key, model):
    calls, terr = [], 0
    for s in TICKETS:
        try:
            data, ms = _post(OPENAI_URL,
                {"model": model, "max_tokens": 200,
                 "messages": [{"role": "user", "content": LLM_PROMPT + s}]},
                {"Authorization": f"Bearer {key}"})
        except urllib.error.HTTPError as e:
            return None, f"HTTP {e.code}: {e.read()[:120]!r}"
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        ok = _schema_ok(text)
        terr += 0 if ok else 1
        u = data.get("usage") or {}
        calls.append({"wall_ms": round(ms, 1),
                      "usage": {"input_tokens": u.get("prompt_tokens"),
                                "output_tokens": u.get("completion_tokens")},
                      "schema_ok": ok})
    return calls, terr


def _schema_ok(text):
    try:
        p = json.loads(text.strip().strip("`").lstrip("json").strip())
        return (p.get("route") in ROUTES and isinstance(p.get("urgency"), int)
                and isinstance(p.get("refund_eligible_prob"), (int, float)))
    except Exception:
        return False


def parse_spec(spec):  # "model:in:out"
    parts = spec.split(":")
    return parts[0], float(parts[1]), float(parts[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="SG")
    ap.add_argument("--anthropic", nargs="*", default=[])
    ap.add_argument("--openai", nargs="*", default=[])
    ap.add_argument("--jev-model", default="jev-latest")
    ap.add_argument("--jev-price-in", type=float, default=0.042)
    args = ap.parse_args()

    out = {"region": args.region, "workload": f"{len(TICKETS)} tickets x 3 decisions",
           "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "models": {}, "errors": {}}

    jkey = os.environ.get("TYPESAFE_API_KEY")
    if jkey:
        calls, terr = run_jev(jkey, args.jev_model)
        m = summarize(calls, args.jev_price_in, 0.0); m["type_errors"] = terr
        m["pricing"] = "announced"; out["models"]["jev"] = m
        out["_jev_calls"] = [c["answers"] for c in calls]

    akey = os.environ.get("ANTHROPIC_API_KEY")
    for spec in args.anthropic:
        model, pin, pout = parse_spec(spec)
        if not akey:
            out["errors"][model] = "no ANTHROPIC_API_KEY"; continue
        calls, terr = run_anthropic(akey, model)
        if calls is None:
            out["errors"][model] = terr; continue
        m = summarize(calls, pin, pout); m["type_errors"] = terr
        m["pricing"] = "published"; out["models"][model] = m

    okey = os.environ.get("OPENAI_API_KEY")
    for spec in args.openai:
        model, pin, pout = parse_spec(spec)
        if not okey:
            out["errors"][model] = "no OPENAI_API_KEY"; continue
        calls, terr = run_openai(okey, model)
        if calls is None:
            out["errors"][model] = terr; continue
        m = summarize(calls, pin, pout); m["type_errors"] = terr
        m["pricing"] = "published"; out["models"][model] = m

    # ratios vs jev
    if "jev" in out["models"]:
        j = out["models"]["jev"]
        for name, m in out["models"].items():
            if name == "jev":
                continue
            m["vs_jev_cheaper_x"] = round(m["cost_usd"] / j["cost_usd"], 1) if j["cost_usd"] else None
            m["vs_jev_slower_x"] = round(m["latency_ms_median"] / j["latency_ms_median"], 1)

    out["honesty"] = [
        "Cost from labeled prices (LLM published, Jev announced/unverified).",
        f"Latency measured from region={args.region}; compare only same-region.",
        "Decision quality/calibration not scored here.",
    ]
    path = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results",
                        f"systemone_matrix_{args.region}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({n: {k: m[k] for k in ("latency_ms_median", "cost_usd",
          "type_errors", "vs_jev_cheaper_x", "vs_jev_slower_x") if k in m}
          for n, m in out["models"].items()}, indent=2))
    if out["errors"]:
        print("errors:", out["errors"])
    print("->", os.path.relpath(path))


if __name__ == "__main__":
    main()
