# DecaState — LinkedIn launch posts

## 🔥 The "paying twice" hook bank (rotate these — this angle lands hardest)

Use one as your first line, tweet, headline, or thumbnail text. Short = shareable.

- **You're paying your LLM twice for the same codebase.** (the payee-named winner)
- **You already paid Anthropic to read your repo. Why are you paying again?**
- **Your OpenAI bill has a line item called "re-reading what it already knew."**
- **You already paid to understand your codebase. Stop paying for it again.**
- **Your AI reads your repo once. You pay for it every single restart.**
- **Stop paying twice to understand the same codebase.**
- **Understand the repo once. Pay once. Not on every restart and every fork.**
- **Your coding agent has amnesia — and you're billed for the re-learning.**
- **Same repo. Same context. Read from zero, ten times a day. That's the tax DecaState deletes.**
- **10 agents, 1 codebase, 10 copies of the same understanding. Why?**
- **Never make your AI rebuild the same state twice.** (the brand line)

---


Four variants. Pick one and attach a visual: the square video (`decastate_launch_1x1.mp4`), the story GIF (`decastate_demo.gif`), or the real-terminal GIF (`decastate_coding.gif` — best for the "on a MacBook" flex). Best times: Tue–Thu, 8–10am your audience's timezone. Reply to every comment in the first 2 hours — that's what the algorithm rewards.

---

## Variant A — the "you're paying twice" hook (recommended)

Your AI coding agent reads your entire repo to understand it.

Then it restarts. And reads the whole thing again. From zero.

Then you spin up a second agent to review the code. It reads everything again.

You're paying to process the same context 3, 5, 10 times a day. Not because it changed — because the state got thrown away.

So I built **DecaState**.

It saves the model's *actual* working memory — the real inference state, not a chat transcript — to disk. Kill the process. Reboot. Wake it → continue **byte-for-byte identical**, with **zero** of the original context re-read.

Measured, on a deliberately tiny model so anyone can reproduce it in minutes:

→ 100% of the redundant prefill: gone
→ Up to 13.7× faster to wake than to rebuild (the gap grows with your context)
→ Fork a new agent from one understanding in ~15 milliseconds

For one agent holding a 100K-token repo, restarted 20× a day, that's 2 MILLION tokens of re-processing eliminated. Per agent. Per day.

The part I care about most: every single claim maps to a script and a results file in the repo. What's proven is proven. What I haven't proven yet, I say so — and I publish the negative experiments too.

100% local. MIT licensed. Your code never leaves your machine.

git clone → `decastate demo .` → watch it happen on your own repo.

⭐ github.com/tempomesh/DecaState

If your agent has ever re-read a repo it already understood, this is the bug I'm fixing. A star genuinely helps it reach the next dev. 🙏

#AI #LLM #DeveloperTools #OpenSource #AppleSilicon #CodingAgents #MachineLearning

---

## Variant B — the builder's story (personal, high-engagement)

I've been building alone, late nights, for weeks.

The idea was simple enough to be annoying: **why does an AI agent forget everything the moment a process restarts?**

It just spent two minutes understanding your codebase. Then — crash, restart, or a second agent — and it does the whole thing over. From scratch. Every time.

That's not a small inefficiency. That's the same expensive work, redone on a loop.

So I made **DecaState**: an AI State Runtime that persists the model's real inference state to disk and wakes it in a fresh process — exact continuation, zero context re-read.

The numbers (all measured, all reproducible on a tiny model in minutes):
• 100% of redundant prefill avoided
• up to 13.7× faster resume
• ~15 ms to fork a new agent from one shared understanding

It's open source (MIT), 100% local, Apple Silicon today.

I'm not going to pretend it does everything — I explicitly list what's proven vs. what isn't, and I publish the failed experiments. That honesty is the whole point.

If this resonates, a ⭐ on GitHub is the single biggest thing that helps a solo project get seen: github.com/tempomesh/DecaState

Happy to answer anything in the comments. 👇

#BuildInPublic #OpenSource #AI #DeveloperTools #LLM #Startups

---

## Variant C — short + punchy (for reshares)

Your coding agent re-reads your whole repo every time it restarts.

DecaState makes it read once, then wake from disk — byte-exact, zero re-prefill.

→ 100% of redundant prefill avoided
→ up to 13.7× faster resume
→ ~15 ms to fork an agent
→ 100% local, MIT, reproduce it in minutes

Keep the state. Change everything else.

⭐ github.com/tempomesh/DecaState

#AI #OpenSource #DeveloperTools

---

## Comment-reply starters (seed the thread yourself with a first comment)

- "Technical detail for anyone curious: it serializes the MLX KV cache with fingerprint + SHA-256 guards, then restores it in a completely separate OS process. Not chat-history replay — the actual tensors. Repro script is in the repo."
- "To be clear about scope: this is same-model, same-runtime today (Apple Silicon / MLX). Cross-model and llama.cpp are on the roadmap and NOT claimed yet. I'd rather under-promise here."
- "The demo runs on a 0.5B model on purpose — so you can verify every number yourself in a couple of minutes instead of trusting my screenshot."

---

## Variant D — the "on a MacBook" flex (great with `decastate_coding.gif`)

No cloud. No API key. No GPU cluster. Just a MacBook.

On an Apple M4 Max (64 GB), DecaState reads my entire repo into the model's real inference state — 8,486 tokens, one native MLX cache — then:

→ checkpoints that understanding (immutable, fingerprint-guarded)
→ forks a fresh "reviewer" agent from it in 0.066 seconds
→ survives a full reboot
→ rolls back byte-exact, with 0 tokens of the repo re-read

The whole thing runs locally on Apple Silicon. Your code and your state never leave the machine.

That's the pitch: your AI understands the codebase once, and never rebuilds it — not after a crash, not after a restart, not for the next agent.

Open source, MIT. `decastate demo .` runs it on your own repo in minutes.

⭐ github.com/tempomesh/DecaState

#AppleSilicon #MLX #LocalLLM #AI #OpenSource #DeveloperTools #MacDev
