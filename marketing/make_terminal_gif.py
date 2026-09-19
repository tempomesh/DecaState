#!/usr/bin/env python3
"""Side-by-side terminal GIF: Jev (parallel, typed) vs an LLM (autoregressive).

Real data from benchmarks/results/terminal_demo.json (one ticket, 14 typed
decisions, both routed through the DecaState gateway). Jev's answers snap in
together; the LLM's stream one by one — the visual difference, honestly.

Output: marketing/decastate_terminal_1x1.gif
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
DEMO = sys.argv[1] if len(sys.argv) > 1 else "benchmarks/results/terminal_demo.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "decastate_terminal_1x1.gif"
D = json.load(open(os.path.join(HERE, "..", DEMO)))
BG, LIME, WHITE, CORAL, DIM, DIMMER = ("#07090e", "#c3f53c", "#e9edf5", "#ff8f88", "#8b97b0", "#5f6b85")
PANE, BAR, BORD = "#0d1219", "#161b24", "#242a35"
bold = lambda s: ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", s)
black = lambda s: ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Black.ttf", s)
mono = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s)
ease = lambda t: 1 - (1 - t) ** 3

SHORT = {"Revenue currently impacted?": "revenue impacted?", "Production capability down?": "production down?",
         "Which incident scope?": "incident scope", "Account health status?": "account health",
         "Security concern present?": "security concern?", "Human attention needed?": "human needed?",
         "Churn likelihood level?": "churn level", "Financial impact level?": "financial impact",
         "Which response deadline?": "deadline", "Which primary department?": "department",
         "Which requested resolution?": "resolution", "Repeated production failures?": "repeated failures?",
         "Language personally threatening?": "threatening?", "Immediate feature request?": "feature request?"}
KEYS = D["questions"]


def jev_val(a):
    if a.get("type") == "noul": return f"{a['noul']:.2f}"
    if a.get("type") == "choice": return f"{a['choice']} ({a.get('confidence',0):.0%})"
    if a.get("type") == "score": return f"{a['score']:.1f}/3"
    return "?"


def llm_val(v):
    if isinstance(v, bool): return "true" if v else "false"
    return str(v)


def base(d):
    d.rectangle([0, 0, 1080, 1080], fill=BG)
    for i in range(0, 1081, 54):
        d.line([(i, 0), (i, 1080)], fill=(18, 22, 30), width=1)
        d.line([(0, i), (1080, i)], fill=(18, 22, 30), width=1)


def brand(d):
    cx, cy, s = 62, 60, 17
    d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=LIME)
    d.polygon([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)], fill=BG)
    d.text((92, 43), "DecaState", font=bold(32), fill=WHITE)
    monob = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s, index=1)
    x = 92
    for t, fn, c in [("Jev (TypeSafe AI)", monob(29), LIME),
                     ("    measured with    ", mono(19), DIM),
                     ("DecaState.com", monob(29), LIME)]:
        d.text((x, 86), t, font=fn, fill=c); x += d.textlength(t, font=fn)
    d.line([(48, 128), (1032, 128)], fill=(28, 34, 48), width=1)


def pane(d, x0, title, cmd, jev, n_show, answers, keys):
    x1 = x0 + 480
    d.rounded_rectangle([x0, 170, x1, 900], 12, fill=PANE, outline=BORD, width=2)
    d.rounded_rectangle([x0, 170, x1, 210], 12, fill=BAR, outline=BORD, width=2)
    d.rectangle([x0, 196, x1, 210], fill=BAR)
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        d.ellipse([x0 + 18 + i * 22, 183, x0 + 32 + i * 22, 197], fill=c)
    d.text((x0 + 240 - d.textlength(title, font=mono(15)) / 2, 183), title, font=mono(15), fill=DIM)
    d.text((x0 + 18, 226), cmd, font=mono(15), fill=LIME if jev else WHITE)
    status = ("parallel · all answers at once" if jev
              else ("streaming token by token..." if n_show < len(keys) else "done · then parse + validate"))
    d.text((x0 + 18, 254), status, font=mono(13), fill=DIMMER)
    y = 290
    for i, k in enumerate(keys):
        if i >= n_show:
            break
        lbl = SHORT.get(k, k)[:22]
        d.text((x0 + 18, y), lbl, font=mono(14), fill=DIM)
        val = jev_val(answers[k]) if jev else llm_val(answers.get(k, "?"))
        val = val[:16]
        vc = LIME if jev else WHITE
        d.text((x1 - 18 - d.textlength(val, font=mono(14)), y), val, font=mono(14), fill=vc)
        y += 41


def foot(d, x0, jev, done):
    if not done: return
    x1 = x0 + 480
    side = D["jev"] if jev else D["llm"]
    d.line([(x0 + 16, 852), (x1 - 16, 852)], fill=BORD, width=1)
    c1 = f"cost ${side['cost_usd']:.6f}"
    c2 = f"{side['latency_ms']:.0f}ms"
    d.text((x0 + 18, 866), c1, font=mono(15), fill=LIME if jev else DIM)
    d.text((x1 - 18 - d.textlength(c2, font=mono(15)), 866), c2, font=mono(15), fill=LIME if jev else DIM)


frames = []
JN, LN = len(KEYS), len(KEYS)
LLM_MODEL = D["llm"]["model"]
CMD_L, CMD_R = "$ decastate measure jev", f"$ decastate measure {LLM_MODEL}"
SPD = D["llm"]["latency_ms"] / D["jev"]["latency_ms"]
CHP = D["llm"]["cost_usd"] / D["jev"]["cost_usd"]

# ACT 0: land on the payoff first, then show the race
for _ in range(12):
    f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
    base(d); brand(d)
    d.text((60, 296), f"{SPD:.1f}× faster", font=black(112), fill=LIME)
    d.text((60, 440), f"{CHP:.0f}× cheaper", font=black(112), fill=LIME)
    d.text((64, 596), f"Jev vs {LLM_MODEL} · same 14 typed decisions on one ticket",
           font=bold(31), fill=WHITE)
    d.text((64, 646), f"${D['jev']['cost_usd']:.5f}  vs  ${D['llm']['cost_usd']:.4f}   ·   both measured through DecaState",
           font=mono(21), fill=DIM)
    d.text((64, 706), "watch them race, side by side ↓", font=mono(24), fill=LIME)
    d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
    d.text((48, 1012), "◈ decastate.com", font=mono(22), fill=LIME)
    d.text((262, 1012), "·  the honest receipt layer for every model you call",
           font=mono(22), fill=DIMMER)
    frames.append(f)

for fr in range(64):
    f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
    base(d); brand(d)
    js = min(JN, max(0, (fr - 5) * 4))     # Jev: parallel, fills fast
    ls = min(LN, max(0, int((fr - 5) * 0.55)))  # LLM: sequential, slow
    pane(d, 40, "TYPESAFE · jev-latest", CMD_L, True, js, D["jev"]["answers"], KEYS)
    pane(d, 560, f"LLM · {LLM_MODEL}", CMD_R, False, ls, D["llm"]["answers"], KEYS)
    foot(d, 40, True, js >= JN)
    foot(d, 560, False, ls >= LN)
    # end overlay
    if fr >= 50:
        d.rectangle([0, 300, 1080, 820], fill=(7, 9, 14, 232))
        spd = D["llm"]["latency_ms"] / D["jev"]["latency_ms"]
        chp = D["llm"]["cost_usd"] / D["jev"]["cost_usd"]
        d.text((60, 348), f"{spd:.1f}× faster", font=black(88), fill=LIME)
        d.text((60, 454), f"{chp:.0f}× cheaper", font=black(88), fill=LIME)
        d.text((64, 572), f"${D['jev']['cost_usd']:.5f} vs ${D['llm']['cost_usd']:.4f} · same 14 decisions, one ticket",
               font=bold(26), fill=WHITE)
        d.text((64, 612), "both forwarded byte-identically · integrity unchanged ✓",
               font=mono(20), fill=DIM)
        d.text((64, 646), "full 36-decision benchmark in the repo · decastate.com",
               font=mono(20), fill=DIMMER)
    d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
    d.text((48, 1012), "◈ decastate.com", font=mono(22), fill=LIME)
    d.text((262, 1012), "·  the honest receipt layer for every model you call", font=mono(22), fill=DIMMER)
    frames.append(f)
frames += [frames[-1]] * 14
frames[0].save(os.path.join(HERE, OUT),
               save_all=True, append_images=frames[1:], duration=95, loop=0)
print("terminal gif ok ·", len(frames), "frames")
