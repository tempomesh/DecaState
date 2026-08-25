# Benchmarks

Only locally measured results belong here. No benchmark claims have been made yet.

## Phase 1 native replay

Run with:

```bash
make phase1
```

The run uses separate Process A and Process B invocations, the MLX-LM native prompt-cache serializer, and the small approved Qwen MLX checkpoint. Results are written to `benchmarks/results/phase1_native_state.json` locally.

Long-context benchmark:

```bash
make bench-long
```

This measures 128, 512, 1,024, and 2,048-token contexts using real MLX execution.

Latest run: all four context lengths produced exact cold-vs-wake continuation agreement. The JSON output records cold total time, wake total time, state size, and measured resume speedup for each length.

## Checkpoint / rollback

Run with:

```bash
make checkpoint
```

The benchmark covers 128, 512, 1,024, and 2,048-token states. C1 and C2 both restore with exact continuation, zero original-prefix re-prefill, correct lineage, and rejection of missing, corrupt, and wrong-fingerprint checkpoints. Raw results are written to `benchmarks/results/checkpoint_rollback.json`.

## Fork correctness

Run with:

```bash
make fork
```

The benchmark uses an exactly 1,024-token base state and creates `coder`, `reviewer`, and `security` physical-copy branches. Native branch-state hashes are distinct, each branch wakes exactly, and the parent remains unchanged. Output-token coincidence is recorded separately because equal short continuations do not imply shared state. Raw results are written to `benchmarks/results/fork_baseline.json`.

## Copy-on-write research

Run with:

```bash
make cow-benchmark
```

The 2,048-token native cache was cloned into three branches using the macOS `clonefile` primitive. Clone creation succeeded, with approximately 0.17–3.65 ms fork latency. However, `st_blocks` physical-allocation measurements showed approximately 1.0× logical-to-physical storage and no measurable change after a one-byte mutation. Result: the file-clone primitive is available, but native KV COW savings are not proven and are not claimed.
