# Jev Engineering — Working Understanding

Status of every fact below: `[D] = from TypeSafe's docs (verified wire format)`,
`[L] = from their launch material (their own numbers, unverified)`,
`[O] = our assessment`.

## 1. What Jev is

A "System One" model: no text generation. You send **state** (unstructured
context) plus **typed questions**; it returns **typed answers with calibrated
probabilities**, all evaluated in parallel in one call. [D]

```
  "a frontier-intelligence function call:
   unstructured state in, typed probabilistic decisions out"

  LLM  : state ──► tokens, one at a time ──► string ──► parse & pray
  JEV  : state ──► all answers at once   ──► typed values + probabilities
```

Trained with RLCD (Reinforcement Learning for Calibrated Decisions):
optimizes for *epistemically honest probabilities*, not human-pleasing
text. [L]

## 2. The three primitives  [D]

```
 +-----------+---------------------------+---------------------------------+
 | PRIMITIVE | QUESTION                  | RETURNS                         |
 +-----------+---------------------------+---------------------------------+
 | Choice    | pick one option           | choice + full probability       |
 |           | from a list (<=255)       | distribution + confidence       |
 | Score     | rate state on an          | prob-weighted score + legend    |
 |           | ordered rubric            | + probabilities + confidence    |
 | Noul      | is this statement true?   | single probability 0..1         |
 +-----------+---------------------------+---------------------------------+
   All three mix in ONE call; each question evaluated independently
   against the same state -> adding questions ~ free, no context-rot.
```

## 3. Wire format  [D — fetched from docs.typesafe.ai]

```
 POST https://api.typesafe.ai/v1/systemone
 Authorization: Bearer <API_KEY>

 request:  { "state": <string|object|array>,
             "model": "jev-latest",
             "questions": { "<id>": {type, instructions, criteria}, ... } }

 response: { "model": "jev-latest",
             "answers": { "<id>": {type, choice|score|noul,
                                   probabilities, confidence} },
             "usage":   { "input_tokens", "output_tokens" } }

 errors: 401 / 422 / 429 / 529 (backoff)
```

## 4. The architecture pattern (their Fig. 1)

```
 +--------------------+        +-------------------+        +--------------------+
 |  LLM / AGENT STATE |        |        JEV        |        | CODE / ORCHESTRATOR|
 |  goal, context,    | state  |  reason, evaluate | typed  |  validate          |
 |  rules, available  |──────► |  plan, select,    |──────► |  apply thresholds  |
 |  actions, history  |        |  act              | answers|  select branch     |
 +--------------------+        |  (decision brain) |        |  execute           |
                               +-------------------+        |  log + verify      |
                                                            +--------------------+
        intelligence lives in the middle; EXECUTION stays in code.
```

## 5. Engineering rules (the 10-step playbook, distilled)  [L/O]

```
 1. SPLIT   intelligence from execution — Jev decides, code acts.
 2. ATOMIC  questions: one gut-check each. "Rate this pitch" -> decompose
            into market / feasibility / differentiation, combine in code.
 3. BATCH   questions, not calls: 13 questions in one call, not 13 calls.
 4. BOUNDED forks only: agent/model/tool/browser-action/human-escalation
            choice points — places where the option set is enumerable.
 5. THRESH  branch on probabilities in YOUR code (risk-based thresholds),
            so tuning = changing a coefficient, not rewriting a prompt.
 6. VERIFY  the loop: State -> Questions -> Action -> Verify. Jev also
            works as the verifier (score/judge/guardrail LLM outputs).
 7. KEEP    Jev OUT of: math, writing, code generation, irreversible
            execution. Code computes, LLMs create, Jev decides.
```

## 6. Claims vs. what is actually established  [O]

```
 +--------------------------------+------------------------------------------+
 | CLAIM                          | HONEST STATUS                            |
 +--------------------------------+------------------------------------------+
 | zero type errors               | structural (schema-constrained output);  |
 |                                | plausible by construction. NOTE: typed   |
 |                                | != correct — the answer can still be     |
 |                                | wrong; calibration is the mitigation.    |
 | 40-200x faster, 70-500ms       | their measurements, West-Coast network;  |
 |                                | independently measurable (we will).      |
 | 193x / 444x workflow gains     | their harness, reference = Astra+Fable   |
 |                                | avg, LLMs run through THEIR wrapper —    |
 |                                | bias admitted by them. Unverified.       |
 | $0.042/MTok in, output free    | announced; possibly subsidized (they     |
 |                                | say so). Verify on a real bill.          |
 | calibrated confidence          | the core research bet; needs labeled     |
 |                                | data to check. Not yet verified by       |
 |                                | anyone independent.                      |
 +--------------------------------+------------------------------------------+
```

## 7. Where it genuinely fits / doesn't  [O]

```
 FITS: routing, triage, scoring, extraction-to-enum, guardrails,
       jailbreak detection, map-reduce classification over big data,
       real-time (<100ms) in-app decisions, high-cardinality choices.
 NOT:  generation of any kind (text/code), math, multi-factor reasoning
       in one question (must decompose), anything irreversible without
       a code/human gate.
```
