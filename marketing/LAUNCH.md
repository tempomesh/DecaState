# DecaState — Launch kit

All assets in this folder are generated from **real, measured runs** on this machine. No mockups, no invented numbers. Every figure traces to a file in `../benchmarks/results/`.

## Assets

| File | Use |
|---|---|
| `decastate_launch.mp4` | 1920×1080, 79 s, voiced launch film — YouTube, Twitter/X, LinkedIn, Product Hunt |
| `decastate_launch_1x1.mp4` | 1080×1080 square (letterboxed) — Instagram, LinkedIn feed, Twitter square |
| `decastate_demo.gif` | Terminal demo loop — README hero, tweets, Slack/Discord |
| `decastate_poster.png` | Video thumbnail / social card |
| `demo_output.txt` | Raw captured `decastate demo .` output |

Regenerate everything: `film.html` → `render_film.cjs` (frames) → ffmpeg (mux) + `vo_*.mp3` (edge-tts, en-US-Andrew).

---

## The hook

**Never make your AI rebuild the same state twice.**

The one-liner that does the work: *your coding agent reads your whole repo, then a restart makes it read the whole thing again — from zero. DecaState saves the model's actual inference state to disk so it never has to.*

---

## Launch post — Twitter/X (thread)

**1/**
Your AI coding agent reads your entire repo to understand it.

Then the process restarts and it reads the whole thing again. From zero. Every time.

I got tired of that. So I built DecaState — it saves the model's *actual* working memory to disk. 🧵

**2/**
Not chat history. The real KV cache — the model's internal understanding of your context.

Kill the process. Reboot. Wake the state → continue **byte-for-byte identical**, with **0 tokens of the original context re-read.**

**3/**
The numbers (measured live, tiny 0.5B proof model so you can verify in minutes):

• 2,048-token context: **13.7× faster** to wake than rebuild
• **100%** of prefill avoided
• Fork a new agent from one understanding: **~15 ms**

The speedup grows with context. At real agent sizes it's the whole ballgame.

**4/**
One understood repo → coder + reviewer + security agents, each independent, each ~15 ms to spin up.

**Fork the work, not the context.**

**5/**
The part I'm proud of: every claim maps to a script and a results file in the repo. What's proven is proven. What isn't (COW savings, cross-model), I explicitly *don't* claim — and I publish the negative results too.

MIT. Apple Silicon. `git clone` → `decastate demo .`

⭐ github.com/tempomesh/DecaState

---

## Launch post — LinkedIn

Coding agents have a memory problem nobody talks about: they rebuild the same context over and over.

An agent spends real time reading your repository — files, architecture, decisions. Then the process dies, or you restart, or you want a second agent for review. And it reads everything again. From scratch. The compute is spent twice, three times, ten times.

I built **DecaState**, an open-source AI State Runtime for Apple Silicon. It persists the model's actual inference state (the KV cache — not a chat transcript) to disk. Wake it in a brand-new process and continue exactly where it stopped, with zero of the original context re-processed.

Measured, on a deliberately tiny proof model so anyone can reproduce it in minutes:
• 13.7× faster to wake than to rebuild at 2,048 tokens (the gap grows with context)
• 100% of eligible prefill avoided, byte-exact continuation
• Fork a new agent from one understanding in ~15 ms

What I care about most: every claim in the repo maps to a runnable script and a results file. The things I haven't proven yet — copy-on-write savings, cross-model migration — I state plainly as *not claimed*, and I publish the negative experiments too. Honesty is the moat.

MIT licensed. `git clone` → `decastate demo .`

github.com/tempomesh/DecaState

---

## Product Hunt tagline

**DecaState — Keep the state. Change everything else.**
Persist, wake, checkpoint, and fork your AI's real inference state. Your coding agent understands the repo once — and never rebuilds it.

---

## Hacker News (Show HN)

**Show HN: DecaState – persist and fork a model's real inference state (MLX)**

I kept watching coding agents re-read the same repository after every restart, so I built a runtime that serializes the actual MLX KV cache to disk and restores it in a fresh process — byte-exact continuation, zero re-prefill of the original context.

It does save/wake across process death, immutable checkpoint/rollback with fingerprint + corruption guards, and physical-copy forks (one understood repo → coder/reviewer/security branches). It does NOT yet do copy-on-write savings or cross-model migration, and I don't claim them — the COW experiment is in the repo as a published negative result.

Everything is a small 0.5B proof model so you can reproduce every number in minutes: `git clone && decastate demo .`. Feedback on the cross-runtime (llama.cpp) direction especially welcome.
