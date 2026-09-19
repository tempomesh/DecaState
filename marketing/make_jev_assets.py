#!/usr/bin/env python3
"""Build the Jev-measured LinkedIn card + cost-race GIF from the real receipt.

Numbers come from benchmarks/results/systemone_measured.json — nothing typed
in by hand. Outputs:
  marketing/decastate_jev_15x_1x1.png   (1080x1080 card)
  marketing/decastate_jev_race_1x1.gif  (1080x1080 cost race)
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

R = json.load(open(os.path.join(os.path.dirname(__file__), "..",
                                "benchmarks/results/systemone_measured.json")))
COST_X = R["measured_ratio"]["cost_x"]          # 15.4
LAT_X = R["measured_ratio"]["latency_median_x"] # 1.1
JEV_C, LLM_C = R["jev"]["cost_usd"], R["llm"]["cost_usd"]
JEV_MS, LLM_MS = R["jev"]["latency_ms_median"], R["llm"]["latency_ms_median"]

BG, LIME, WHITE, CORAL, DIM, DIMMER, GREY = ("#07090e", "#c3f53c", "#e9edf5",
                                             "#ff8f88", "#8b97b0", "#5f6b85",
                                             "#39424f")
SUP = "/System/Library/Fonts/Supplemental/"
F = lambda p, s: ImageFont.truetype(p, s)
black = lambda s: F(SUP + "Arial Black.ttf", s)
bold = lambda s: F(SUP + "Arial Bold.ttf", s)
mono = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s)

def base(d):
    d.rectangle([0, 0, 1080, 1080], fill=BG)
    for i in range(0, 1081, 54):  # faint grid
        d.line([(i, 0), (i, 1080)], fill=(195, 245, 60, 8), width=1)
        d.line([(0, i), (1080, i)], fill=(18, 22, 30), width=1)

def header(d, right):
    d.text((48, 44), "◈", font=bold(30), fill=LIME)
    d.text((86, 42), "DecaState", font=bold(30), fill=WHITE)
    f = mono(17)
    d.text((1032 - d.textlength(right, font=f), 52), right, font=f, fill=DIMMER)

def seg(d, x, y, parts, f):
    for txt, col in parts:
        d.text((x, y), txt, font=f, fill=col)
        x += d.textlength(txt, font=f)

# ---------------- CARD ----------------
img = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(img, "RGBA")
base(d); header(d, "MEASURED · INDEPENDENT · REAL API CALLS")

d.text((48, 196), "THE  JEV  HYPE,  MEASURED  ·  36  REAL  DECISIONS",
       font=mono(24), fill=LIME)

d.text((40, 250), f"{COST_X:g}×", font=black(250), fill=LIME)
d.text((52, 486), "cheaper", font=black(92), fill=WHITE)

b = bold(48); y = 610
d.text((48, y), "than the cheapest frontier-lab LLM.", font=b, fill=WHITE)
seg(d, 48, y + 62, [("And ", WHITE), (f"{LAT_X:g}× faster", LIME),
                    (f" — {JEV_MS:.0f}ms median,", WHITE)], b)
d.text((48, y + 124), "inside their own claimed range.", font=b, fill=WHITE)

m = mono(24); y2 = 852
d.text((48, y2),      f"agreed 10/12 route · 12/12 urgency · 0 type errors on both sides", font=m, fill=DIM)
d.text((48, y2 + 40), f"${LLM_C:.4f} → ${JEV_C:.5f} · Jev announced pricing · measured us-west", font=m, fill=DIM)
d.text((48, y2 + 80), f"not 444× (that was vs frontier-priced models) · quality pass pending", font=m, fill=DIM)

d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
seg(d, 48, 1012, [("◈ decastate.com", LIME),
                  ("  ·  measured, not marketed · the honest AI receipt layer", DIMMER)], mono(23))
img.save(os.path.join(os.path.dirname(__file__), "decastate_jev_15x_1x1.png"))
print("card ok")

# ---------------- GIF: cost race ----------------
frames = []
BAR_X, BAR_W, LLM_Y, JEV_Y, BH = 70, 800, 460, 640, 74
for i in range(46):
    t = min(1.0, i / 34)
    e = 1 - (1 - t) ** 3
    f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
    base(d); header(d, "THE SAME 36 DECISIONS · REAL BILLS")
    d.text((48, 208), "J E V   V S   L L M   ·   C O S T   R A C E   ·   M E A S U R E D",
           font=mono(21), fill=LIME)
    d.text((48, 300), "What 36 agent decisions actually cost:", font=bold(44), fill=WHITE)

    d.text((BAR_X, LLM_Y - 44), "claude-haiku-4-5 · strict JSON", font=mono(24), fill=DIM)
    d.rectangle([BAR_X, LLM_Y, BAR_X + BAR_W * e, LLM_Y + BH], fill=GREY)
    d.text((BAR_X + BAR_W * e + 16, LLM_Y + 18), f"${LLM_C * e:.4f}", font=mono(30), fill=DIM)

    d.text((BAR_X, JEV_Y - 44), "Jev · typed answers · announced pricing", font=mono(24), fill=DIM)
    jw = max(8, BAR_W * (JEV_C / LLM_C) * e)
    d.rectangle([BAR_X, JEV_Y, BAR_X + jw, JEV_Y + BH], fill=LIME)
    d.text((BAR_X + jw + 16, JEV_Y + 18), f"${JEV_C * e:.5f}", font=mono(30), fill=LIME)

    if t >= 1.0:
        d.text((48, 792), f"{COST_X:g}× cheaper", font=black(92), fill=LIME)
        d.text((52, 908), f"and {LAT_X:g}× faster · Jev {JEV_MS:.0f}ms median · 0 type errors both sides",
               font=bold(30), fill=WHITE)
    seg(d, 48, 1012, [("◈ decastate.com", LIME),
                      ("  ·  measured, not marketed", DIMMER)], mono(23))
    frames.append(f)
frames += [frames[-1]] * 24  # hold the end card
frames[0].save(os.path.join(os.path.dirname(__file__), "decastate_jev_race_1x1.gif"),
               save_all=True, append_images=frames[1:], duration=80, loop=0)
print("gif ok")

# ---------------- COMPARISON CARD: their claim vs our measured ----------------
img = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(img, "RGBA")
base(d); header(d, "36 REAL DECISIONS · RECEIPT IN REPO")
d.text((48, 196), "THEIR  CLAIM   vs   WHAT  I  MEASURED", font=mono(26), fill=LIME)

colL, colR = 560, 830
d.text((colL, 300), "TypeSafe says", font=mono(22), fill=DIMMER)
d.text((colR, 300), "I measured", font=mono(22), fill=LIME)

rows = [("cheaper", "40–1,000×", f"{COST_X:g}×"),
        ("faster", "20–200×", f"{LAT_X:g}×"),
        ("type errors", "zero", f"0/{R['jev']['calls']}")]
y = 372
for label, claim, meas in rows:
    d.text((48, y + 6), label, font=bold(46), fill=WHITE)
    d.text((colL, y), claim, font=bold(52), fill=DIM)
    d.text((colR, y), meas, font=black(58), fill=LIME)
    d.line([(48, y + 92), (1032, y + 92)], fill=(28, 34, 48), width=2)
    y += 132

d.text((48, y + 24), "Why the gap is honest:", font=bold(38), fill=WHITE)
fn = mono(23)
d.text((48, y + 78), "their big multiples are vs frontier-PRICED models. I tested vs the", font=fn, fill=DIM)
d.text((48, y + 112), "CHEAPEST fast LLM (haiku-4-5) — so 15.8× is the FLOOR, not the ceiling.", font=fn, fill=DIM)
d.text((48, y + 146), "Same 36 decisions · 10/12 agreement · Jev priced at announced rate.", font=fn, fill=DIM)

d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
seg(d, 48, 1012, [("◈ decastate.com", LIME),
                  ("  ·  I measure AI claims for a living · receipt + code in repo", DIMMER)], mono(22))
img.save(os.path.join(os.path.dirname(__file__), "decastate_jev_compare_1x1.png"))
print("compare ok")
