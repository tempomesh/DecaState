#!/usr/bin/env python3
"""Viral showcase GIF: Jev vs the frontier lineup on the same 36 decisions.

Three acts:
  1. intro     — the question ("36 real agent decisions")
  2. the race  — animated cost bars, 4 frontier LLMs vs Jev's sliver
  3. the point — typed not text / 0 type errors / up to 308x cheaper

All cost numbers read from benchmarks/results/systemone_matrix_SG.json
(cost is region-independent). Output: marketing/decastate_jev_showcase_1x1.gif
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
D = json.load(open(os.path.join(HERE, "..", "benchmarks/results/systemone_matrix_SG.json")))
PRETTY = {"claude-fable-5": "Fable 5", "gpt-6-astra": "GPT-6 Astra",
          "claude-opus-5": "Opus 5", "gpt-5.6-sol": "GPT-5.6 Sol"}
ASSUMED = {"gpt-6-astra"}
JEV_C = D["models"]["jev"]["cost_usd"]
rows = sorted([(PRETTY[n], m["cost_usd"], m["vs_jev_cheaper_x"], n)
               for n, m in D["models"].items() if n in PRETTY],
              key=lambda r: r[1], reverse=True)
TOPX = rows[0][2]  # 308.7

BG, LIME, WHITE, CORAL, DIM, DIMMER, GREY = ("#07090e", "#c3f53c", "#e9edf5",
    "#ff8f88", "#8b97b0", "#5f6b85", "#39424f")
SUP = "/System/Library/Fonts/Supplemental/"
black = lambda s: ImageFont.truetype(SUP + "Arial Black.ttf", s)
bold = lambda s: ImageFont.truetype(SUP + "Arial Bold.ttf", s)
mono = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s)


def base(d):
    d.rectangle([0, 0, 1080, 1080], fill=BG)
    for i in range(0, 1081, 54):
        d.line([(i, 0), (i, 1080)], fill=(18, 22, 30), width=1)
        d.line([(0, i), (1080, i)], fill=(18, 22, 30), width=1)


def header(d):
    d.text((48, 44), "◈", font=bold(30), fill=LIME)
    d.text((86, 42), "DecaState", font=bold(30), fill=WHITE)
    r = "MEASURED · RECEIPTS IN REPO"
    d.text((1032 - d.textlength(r, font=mono(17)), 52), r, font=mono(17), fill=DIMMER)


def footer(d):
    d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
    d.text((48, 1012), "◈ decastate.com", font=mono(22), fill=LIME)
    d.text((262, 1012), "·  I measure AI claims for a living", font=mono(22), fill=DIMMER)


def ease(t):
    return 1 - (1 - t) ** 3


frames = []
BAR_X, BAR_MAX = 360, 470
ROW_Y0, ROW_H = 360, 118


def race_frame(prog, show_point=False):
    f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
    base(d); header(d)
    d.text((48, 190), "SAME 36 AGENT DECISIONS · JEV vs THE FRONTIER",
           font=mono(24), fill=LIME)
    d.text((48, 232), "cost to make the exact same 36 typed decisions", font=mono(20), fill=DIMMER)
    # 4 LLM rows (grey) + Jev row (lime)
    allrows = rows + [("Jev", JEV_C, 1, "jev")]
    for i, (name, cost, x, key) in enumerate(allrows):
        y = ROW_Y0 + i * ROW_H
        is_jev = key == "jev"
        col = LIME if is_jev else WHITE
        d.text((48, y), name, font=bold(38), fill=col)
        w = max(6 if is_jev else 2, BAR_MAX * (cost / rows[0][1]) * ease(prog))
        d.rectangle([BAR_X, y + 6, BAR_X + w, y + 52],
                    fill=(LIME if is_jev else GREY))
        star = "*" if key in ASSUMED else ""
        lab = (f"${cost*ease(prog):.5f}  baseline" if is_jev
               else f"${cost*ease(prog):.4f}  · {x:g}×{star}")
        d.text((BAR_X + w + 14, y + 8), lab, font=mono(26),
               fill=(LIME if is_jev else DIM))
    if show_point:
        d.rectangle([0, 300, 1080, 1080], fill=(7, 9, 14, 236))
        d.text((44, 344), f"{TOPX:g}×", font=black(150), fill=LIME)
        d.text((52, 520), "cheaper than the priciest frontier model,", font=bold(40), fill=WHITE)
        d.text((52, 566), "on the exact same 36 decisions.", font=bold(40), fill=WHITE)
        y = 648
        for t in ["typed answers your code runs directly — not a paragraph to parse",
                  "0 type errors · frontier LLMs broke the schema in our runs; Jev can't",
                  "one parallel call · measured, not quoted · receipts in the repo"]:
            d.text((48, y), "▸ " + t, font=mono(23), fill=DIM); y += 44
    footer(d)
    return f


# ACT 1: intro
for i in range(8):
    f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
    base(d); header(d)
    d.text((48, 400), "Everyone's quoting Jev's numbers.", font=bold(46), fill=DIM)
    d.text((48, 470), "So I measured them.", font=black(72), fill=LIME)
    d.text((48, 600), "36 real agent decisions · Jev vs 4 frontier models",
           font=mono(26), fill=WHITE)
    d.text((48, 644), "same workload · real bills · both hemispheres", font=mono(22), fill=DIMMER)
    footer(d)
    frames.append(f)
# ACT 2: the race
for i in range(30):
    frames.append(race_frame(min(1.0, i / 24)))
# ACT 3: the point
for i in range(26):
    frames.append(race_frame(1.0, show_point=True))

frames[0].save(os.path.join(HERE, "decastate_jev_showcase_1x1.gif"),
               save_all=True, append_images=frames[1:], duration=90, loop=0)
print("showcase gif ok ·", len(frames), "frames")
