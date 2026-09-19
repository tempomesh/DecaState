#!/usr/bin/env python3
"""Three matched LinkedIn GIFs (identical format) telling one story:

  1. decastate_ln_1_result_1x1.gif    THE RESULT   — Jev vs the frontier
  2. decastate_ln_2_table_1x1.gif     THE TABLE    — cross-comparison, revealed
  3. decastate_ln_3_decastate_1x1.gif THE PRODUCT  — how DecaState measured it

Data: benchmarks/results/systemone_matrix_US.json (fair latency) and the real
gateway receipt from the byte-identical Jev call. Shared header/footer/style.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
US = json.load(open(os.path.join(HERE, "..", "benchmarks/results/systemone_matrix_US.json")))
PRETTY = {"claude-fable-5": "Fable 5", "gpt-6-astra": "GPT-6 Astra",
          "claude-opus-5": "Opus 5", "gpt-5.6-sol": "GPT-5.6 Sol"}
ASSUMED = {"gpt-6-astra"}
rows = sorted([(PRETTY[n], m["cost_usd"], m["vs_jev_cheaper_x"], m["vs_jev_slower_x"], n)
               for n, m in US["models"].items() if n in PRETTY],
              key=lambda r: r[1], reverse=True)
JEV_C = US["models"]["jev"]["cost_usd"]
JEV_MS = US["models"]["jev"]["latency_ms_median"]
TOPX, TOPFAST = rows[0][2], rows[0][3]

BG, LIME, WHITE, CORAL, DIM, DIMMER, GREY = ("#07090e", "#c3f53c", "#e9edf5",
    "#ff8f88", "#8b97b0", "#5f6b85", "#39424f")
SUP = "/System/Library/Fonts/Supplemental/"
black = lambda s: ImageFont.truetype(SUP + "Arial Black.ttf", s)
bold = lambda s: ImageFont.truetype(SUP + "Arial Bold.ttf", s)
mono = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s)
ease = lambda t: 1 - (1 - t) ** 3


def base(d):
    d.rectangle([0, 0, 1080, 1080], fill=BG)
    for i in range(0, 1081, 54):
        d.line([(i, 0), (i, 1080)], fill=(18, 22, 30), width=1)
        d.line([(0, i), (1080, i)], fill=(18, 22, 30), width=1)


def header(d, right="MEASURED · RECEIPTS IN REPO"):
    d.text((48, 44), "◈", font=bold(30), fill=LIME)
    d.text((86, 42), "DecaState", font=bold(30), fill=WHITE)
    d.text((1032 - d.textlength(right, font=mono(17)), 52), right, font=mono(17), fill=DIMMER)


def footer(d, tag="measured, not marketed · receipts in the repo"):
    d.line([(48, 990), (1032, 990)], fill=(28, 34, 48), width=2)
    d.text((48, 1012), "◈ decastate.com", font=mono(22), fill=LIME)
    d.text((262, 1012), "·  " + tag, font=mono(22), fill=DIMMER)


def save(frames, name, dur=90):
    frames[0].save(os.path.join(HERE, name), save_all=True,
                   append_images=frames[1:], duration=dur, loop=0)
    print(name, len(frames), "frames")


# ============ GIF 1: THE RESULT ============
def gif_result():
    frames = []
    for _ in range(8):
        f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
        base(d); header(d)
        d.text((48, 400), "Jev launched this week.", font=bold(46), fill=DIM)
        d.text((48, 470), "So I measured it.", font=black(76), fill=LIME)
        d.text((48, 606), "36 real agent decisions · Jev vs 4 frontier models",
               font=mono(25), fill=WHITE)
        d.text((48, 648), "same workload · real bills · both hemispheres", font=mono(21), fill=DIMMER)
        footer(d); frames.append(f)

    def race(prog, point=False):
        f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
        base(d); header(d)
        d.text((48, 190), "COST TO MAKE THE SAME 36 DECISIONS", font=mono(24), fill=LIME)
        allr = [(n, c, x) for n, c, x, _, _ in rows] + [("Jev", JEV_C, 1)]
        for i, (name, cost, x) in enumerate(allr):
            y = 300 + i * 116; jev = name == "Jev"
            d.text((48, y), name, font=bold(38), fill=(LIME if jev else WHITE))
            w = max(6 if jev else 2, 450 * (cost / rows[0][1]) * ease(prog))
            d.rectangle([360, y + 6, 360 + w, y + 52], fill=(LIME if jev else GREY))
            star = "*" if name == "GPT-6 Astra" else ""
            lab = ("$0.00025  baseline" if jev else f"${cost*ease(prog):.4f} · {x:g}×{star}")
            d.text((360 + w + 14, y + 10), lab, font=mono(24), fill=(LIME if jev else DIM))
        if point:
            d.rectangle([0, 300, 1080, 1080], fill=(7, 9, 14, 238))
            d.text((44, 344), f"{TOPX:g}×", font=black(150), fill=LIME)
            d.text((52, 522), f"cheaper & {TOPFAST:g}× faster than the priciest", font=bold(38), fill=WHITE)
            d.text((52, 568), "frontier model — same 36 decisions.", font=bold(38), fill=WHITE)
            yy = 660
            for t in ["typed answers your code runs directly — not text to parse",
                      "0 type errors · measured through the DecaState gateway",
                      "every number reproducible · receipts in the repo"]:
                d.text((48, yy), "▸ " + t, font=mono(23), fill=DIM); yy += 44
        footer(d); return f
    for i in range(28):
        frames.append(race(min(1.0, i / 22)))
    for _ in range(22):
        frames.append(race(1.0, point=True))
    save(frames, "decastate_ln_1_result_1x1.gif")


# ============ GIF 2: THE TABLE ============
def gif_table():
    frames = []
    order = list(rows)
    total = 8 + len(order) * 6 + 22

    def frame(reveal, tail=False):
        f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
        base(d); header(d, "SAME 36 DECISIONS · FAIR LATENCY · US-WEST")
        d.text((48, 186), "JEV vs THE FRONTIER", font=mono(26), fill=LIME)
        d.text((48, 228), "all excellent models — different jobs", font=mono(20), fill=DIMMER)
        hy = 286
        for x, t in [(440, "cheaper"), (760, "faster")]:
            d.text((x, hy), t, font=mono(22), fill=DIMMER)
        d.text((48, hy), "model", font=mono(22), fill=DIMMER)
        d.line([(48, hy + 34), (1032, hy + 34)], fill=(28, 34, 48), width=2)
        y = hy + 54
        d.text((48, y), "Jev", font=black(40), fill=LIME)
        d.text((440, y + 4), "—", font=bold(36), fill=DIM)
        d.text((760, y + 4), f"{JEV_MS:.0f}ms", font=black(34), fill=LIME)
        y += 82
        for i, (name, cost, cx, sx, key) in enumerate(order):
            if i >= reveal:
                break
            star = "*" if key in ASSUMED else ""
            d.text((48, y), name, font=bold(38), fill=WHITE)
            d.text((440, y + 4), f"{cx:g}×{star}", font=black(34), fill=LIME)
            d.text((760, y + 4), f"{sx:g}×", font=black(34), fill=WHITE)
            d.line([(48, y + 64), (1032, y + 64)], fill=(20, 25, 35), width=1)
            y += 82
        if tail:
            d.text((48, y + 20), "For narrow decisions: cheaper & faster. For writing &",
                   font=mono(21), fill=DIM)
            d.text((48, y + 52), "reasoning: you still want these models. Pick the right",
                   font=mono(21), fill=DIM)
            d.text((48, y + 84), "tool — and measure it with DecaState.", font=mono(21), fill=LIME)
        footer(d); return f
    for _ in range(8):
        frames.append(frame(0))
    for r in range(1, len(order) + 1):
        for _ in range(6):
            frames.append(frame(r))
    for _ in range(22):
        frames.append(frame(len(order), tail=True))
    save(frames, "decastate_ln_2_table_1x1.gif")


# ============ GIF 3: THE PRODUCT (how DecaState measured it) ============
def gif_decastate():
    frames = []
    boxes = [("YOUR APP", 120), ("◈ DECASTATE", 470, True), ("ANY MODEL", 820)]
    BW, BH, BY = 240, 92, 430

    def scene(dot_t, receipt_t, intro_t):
        f = Image.new("RGB", (1080, 1080)); d = ImageDraw.Draw(f, "RGBA")
        base(d); header(d)
        d.text((48, 180), "HOW I MEASURED ALL OF IT", font=mono(24), fill=LIME)
        d.text((48, 222), "the same layer that can measure YOUR API bills", font=mono(20), fill=DIMMER)
        # three boxes
        cxs = [180, 540, 900]
        for (label, _, *hero), cx in zip(boxes, cxs):
            is_hero = bool(hero)
            x0, x1 = cx - BW // 2, cx + BW // 2
            d.rounded_rectangle([x0, BY, x1, BY + BH], 12,
                                fill=("#10160c" if is_hero else "#0d1219"),
                                outline=(LIME if is_hero else "#1c2230"), width=2)
            fnt = bold(24) if is_hero else mono(20)
            d.text((cx - d.textlength(label, font=fnt) / 2, BY + 32), label,
                   font=fnt, fill=(LIME if is_hero else WHITE))
        d.text((cxs[1] - 150, BY + BH + 12), "byte-identical · SHA-256 · your key",
               font=mono(15), fill=DIMMER)
        # traveling dot (app->deca->model->back)
        if dot_t is not None:
            path = [(cxs[0], BY + BH // 2), (cxs[1], BY + BH // 2),
                    (cxs[2], BY + BH // 2), (cxs[1], BY + BH // 2)]
            seg = dot_t * 3
            i = min(2, int(seg)); fr = seg - i
            x = path[i][0] + (path[i + 1][0] - path[i][0]) * fr
            d.ellipse([x - 9, BY + BH // 2 - 9, x + 9, BY + BH // 2 + 9], fill=LIME)
        # receipt slides up
        if receipt_t > 0:
            ry = int(1080 - (1080 - 600) * ease(receipt_t))
            d.rounded_rectangle([90, ry, 990, ry + 340], 16, fill="#0d1219", outline="#1c2230", width=2)
            d.text((120, ry + 26), "DECASTATE RECEIPT", font=mono(18), fill=LIME)
            lines = [("model", "jev-latest"),
                     ("prompt integrity", "unchanged  ✓"),
                     ("cache", "MISS — Jev has no prompt cache"),
                     ("saving", "not claimed (nothing to claim, honestly)")]
            yy = ry + 74
            for k, v in lines:
                d.text((120, yy), k, font=mono(20), fill=DIM)
                d.text((470, yy), v, font=mono(20), fill=WHITE); yy += 48
            d.text((120, yy + 6), "LLMs, self-hosted, and decision models — one honest ledger.",
                   font=mono(18), fill=DIMMER)
        if intro_t:
            d.rectangle([0, 300, 1080, 1080], fill=(7, 9, 14, 232))
            d.text((48, 430), "DecaState", font=black(96), fill=LIME)
            d.text((52, 560), "forwards every API call byte-for-byte and", font=bold(38), fill=WHITE)
            d.text((52, 606), "proves what each one actually cost.", font=bold(38), fill=WHITE)
            d.text((52, 690), "That's how I measured Jev. It's what it does", font=mono(24), fill=DIM)
            d.text((52, 726), "for your bills too — every model, one receipt.", font=mono(24), fill=DIM)
        footer(d, "the honest receipt layer · open source · MIT"); return f
    for i in range(10):
        frames.append(scene(None, 0, True))
    for i in range(24):
        frames.append(scene(min(1.0, i / 20), 0, False))
    for i in range(20):
        frames.append(scene(1.0, min(1.0, i / 12), False))
    for _ in range(14):
        frames.append(scene(1.0, 1.0, False))
    save(frames, "decastate_ln_3_decastate_1x1.gif")


gif_result()
gif_table()
gif_decastate()
