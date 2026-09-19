#!/usr/bin/env python3
"""Build the benchmark-matrix assets from systemone_matrix_{SG,US}.json.

Outputs (1080x1080), only for data that exists:
  decastate_matrix_cost_1x1.png    cost ranking (region-independent)
  decastate_matrix_us_1x1.png      cheaper + faster, US (fair latency)
  decastate_matrix_sg_1x1.png      cheaper + faster, SG
  decastate_matrix_race_1x1.gif    cost race, all models vs Jev

Cost is final; latency is per-region. Astra pricing is flagged assumed via
ASSUMED set below (asterisked on the cards).
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "..", "benchmarks", "results")
ASSUMED_PRICING = set()  # Astra pricing confirmed 10/50

PRETTY = {"jev": "Jev", "claude-fable-5": "Fable 5", "claude-opus-5": "Opus 5",
          "gpt-6-astra": "GPT-6 Astra", "gpt-5.6-sol": "GPT-5.6 Sol",
          "claude-sonnet-5": "Sonnet 5", "claude-haiku-4-5": "Haiku 4.5"}
BG, LIME, WHITE, CORAL, DIM, DIMMER, GREY = ("#07090e", "#c3f53c", "#e9edf5",
    "#ff8f88", "#8b97b0", "#5f6b85", "#39424f")
SUP = "/System/Library/Fonts/Supplemental/"
black = lambda s: ImageFont.truetype(SUP + "Arial Black.ttf", s)
bold = lambda s: ImageFont.truetype(SUP + "Arial Bold.ttf", s)
mono = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s)


def load(region):
    p = os.path.join(RES, f"systemone_matrix_{region}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def base(d):
    d.rectangle([0, 0, 1080, 1080], fill=BG)
    for i in range(0, 1081, 54):
        d.line([(i, 0), (i, 1080)], fill=(18, 22, 30), width=1)
        d.line([(0, i), (1080, i)], fill=(18, 22, 30), width=1)


def header(d, right):
    d.text((48, 44), "◈", font=bold(30), fill=LIME)
    d.text((86, 42), "DecaState", font=bold(30), fill=WHITE)
    d.text((1032 - d.textlength(right, font=mono(17)), 52), right, font=mono(17), fill=DIMMER)


def footer(d):
    d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
    x = 48
    for t, c in [("◈ decastate.com", LIME),
                 ("  ·  measured, not marketed · receipts in the repo", DIMMER)]:
        d.text((x, 1012), t, font=mono(22), fill=c); x += d.textlength(t, font=mono(22))


def others_sorted(data, key):
    xs = [(n, m) for n, m in data["models"].items() if n != "jev"]
    return sorted(xs, key=lambda nm: nm[1].get(key, 0), reverse=True)


def cost_card(data):
    img = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(img, "RGBA")
    base(d); header(d, "SAME 36 DECISIONS · COST IS REGION-INDEPENDENT")
    d.text((48, 190), "HOW MUCH CHEAPER IS JEV?", font=mono(26), fill=LIME)
    d.text((48, 232), "cost per 36 real agent decisions, vs each frontier model",
           font=mono(21), fill=DIMMER)
    rows = others_sorted(data, "vs_jev_cheaper_x")
    maxx = max(m["vs_jev_cheaper_x"] for _, m in rows)
    y = 320; bh = 96
    for name, m in rows:
        star = "*" if name in ASSUMED_PRICING else ""
        d.text((48, y), PRETTY.get(name, name), font=bold(40), fill=WHITE)
        w = 455 * (m["vs_jev_cheaper_x"] / maxx)
        d.rectangle([320, y + 6, 320 + w, y + 52], fill=LIME)
        d.text((320 + w + 14, y + 8), f"{m['vs_jev_cheaper_x']:g}×{star}",
               font=black(40), fill=LIME)
        y += bh
    d.text((48, y + 10), "← Jev did the same 36 decisions for $0.00025, 0 type errors.",
           font=mono(22), fill=DIM)
    if any(n in ASSUMED_PRICING for n, _ in rows):
        d.text((48, y + 44), "* pricing assumed pending confirmation · all others published rates",
               font=mono(19), fill=DIMMER)
    footer(d)
    img.save(os.path.join(HERE, "decastate_matrix_cost_1x1.png")); print("cost card ok")


def region_card(data, region):
    img = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(img, "RGBA")
    base(d); tag = "FAIR LATENCY · US-WEST" if region == "US" else "LATENCY · SINGAPORE"
    header(d, f"SAME 36 DECISIONS · {tag}")
    d.text((48, 190), f"JEV vs THE FRONTIER · {region}", font=mono(26), fill=LIME)
    d.text((48, 232), "same 36 decisions · these are all excellent models — different jobs",
           font=mono(20), fill=DIMMER)
    hy = 288
    for x, t in [(440, "cheaper"), (760, "faster")]:
        d.text((x, hy), t, font=mono(22), fill=DIMMER)
    d.text((48, hy), "model", font=mono(22), fill=DIMMER)
    d.line([(48, hy + 34), (1032, hy + 34)], fill=(28, 34, 48), width=2)
    y = hy + 54
    d.text((48, y), "Jev", font=black(40), fill=LIME)
    d.text((440, y + 4), "—", font=bold(36), fill=DIM)
    d.text((760, y + 4), f"{data['models']['jev']['latency_ms_median']:.0f}ms", font=black(34), fill=LIME)
    y += 82
    for name, m in others_sorted(data, "vs_jev_cheaper_x"):
        star = "*" if name in ASSUMED_PRICING else ""
        d.text((48, y), PRETTY.get(name, name), font=bold(38), fill=WHITE)
        d.text((440, y + 4), f"{m['vs_jev_cheaper_x']:g}×{star}", font=black(34), fill=LIME)
        d.text((760, y + 4), f"{m['vs_jev_slower_x']:g}×", font=black(34), fill=WHITE)
        d.line([(48, y + 64), (1032, y + 64)], fill=(20, 25, 35), width=1)
        y += 82
    d.text((48, y + 20), "For narrow decisions Jev is cheaper & faster. For writing and",
           font=mono(21), fill=DIM)
    d.text((48, y + 52), "reasoning, you still want these models. Pick the right tool — and",
           font=mono(21), fill=DIM)
    d.text((48, y + 84), "measure it. cheaper = cost/36 · faster = median latency vs Jev.",
           font=mono(21), fill=DIM)
    if region == "US":
        d.text((48, y + 124), "measured from OCI Phoenix · both regions + type-safety data in the repo",
               font=mono(18), fill=DIMMER)
    footer(d)
    img.save(os.path.join(HERE, f"decastate_matrix_{region.lower()}_1x1.png"))
    print(f"{region} card ok")


def main():
    sg, us = load("SG"), load("US")
    src = us or sg
    if not src:
        print("no matrix data yet"); return
    cost_card(src)
    if sg: region_card(sg, "SG")
    if us: region_card(us, "US")


if __name__ == "__main__":
    main()
