---
name: gpu-budget
description: Run GPU work on this machine (WSL2 + RTX 4090) without making the user's desktop unusable. Use this BEFORE launching any training, inference, or benchmark that touches the GPU — it supplies the memory cap and the adaptive duty-cycle controller that yields to foreground use. Also use when the user asks about GPU contention, "don't hog the GPU", limiting VRAM, or why a GPU job is slow.
---

# GPU budget on this machine

## What is and is not possible here

Measured on 2026-08-23. Do not promise partitioning — it does not exist on this hardware.

| Mechanism | Status | Evidence |
|---|---|---|
| MIG (hardware partition) | **Unavailable** | GeForce cards do not support it; `mig.mode.current` returns `[N/A]` |
| MPS (SM share limit) | **Unavailable** | `nvidia-cuda-mps-control` absent; MPS is not supported under WSL2 |
| Power limit / compute mode | **Unavailable** | `nvidia-smi -pl` → `Insufficient Permissions`; the driver lives on the Windows side |
| Per-process GPU attribution | **Unavailable** | `--query-compute-apps` and `pmon` both return empty inside WSL |
| VRAM cap per process | **Works** | `torch.cuda.set_per_process_memory_fraction` |
| Duty-cycle throttle | **Works** | target 0.6 → measured 0.595; target 0.4 → measured 0.406 |

So: **no preemption, no partitioning — only cooperative yielding.** Our process shrinks itself. It cannot stop the user's work from slowing down, and it cannot guarantee any total-GPU-utilization number.

## The one non-obvious trick

Per-process attribution is unavailable, so the foreground load cannot be queried directly. Instead:

> **Sample total GPU utilization *during our own throttle-sleep windows*. That reading is the other processes' load.**

`AdaptiveBudget` is built on this and needs no extra privileges.

## Setup

Authoritative copies live in this skill's `scripts/`. Sync them into the executor before use:

```bash
wsl.exe -e bash -lc 'cp "/mnt/c/Users/Wen Zhengyu/Agent_workspace/.claude/skills/gpu-budget/scripts/"*.py ~/fastrelight/analysis/'
```

## Usage — adaptive (default; prefer this)

Yields automatically when the user is active. Use for anything long-running.

```python
import sys; sys.path.insert(0, "/home/wzy27/fastrelight/analysis")
from adaptive_budget import AdaptiveBudget

with AdaptiveBudget(mem_fraction=0.6) as budget:
    for step in range(num_steps):
        with budget():          # wrap ONE unit of GPU work
            loss = train_step()
    print(budget.summary())
```

Default policy — `other_util` is the foreground load estimated during sleep windows:

| other_util | our target duty |
|---|---|
| < 25% | 0.85 |
| 25–50% | 0.60 |
| 50–75% | 0.35 |
| ≥ 75% | 0.15 |

Free VRAM below `min_free_mb` (default 3000) forces duty to 0.15 regardless.

Override with `AdaptiveBudget(policy=[(30, 0.9), (60, 0.5), (101, 0.2)])`; bounds ascending, last entry is the fallback.

## Usage — fixed (benchmarks, or when a stable rate matters)

```python
from gpu_budget import MemoryCap, DutyThrottle
MemoryCap(0.6).apply()
thr = DutyThrottle(target=0.6)
for step in range(n):
    with thr:
        work()
print(thr.summary())
```

## Rules

1. **Never launch GPU work on this machine without one of these wrappers.** The user runs their desktop on the same card.
2. Wrap exactly one unit of work per `with` block. Too coarse (a whole epoch) makes sleeps lumpy and the desktop stutter; too fine (a single kernel) makes the sync overhead dominate. Target roughly 50–500 ms of work per block.
3. Both wrappers call `torch.cuda.synchronize()` on exit. That is required for the timing to be real, and it does cost throughput.
4. Report the measured duty from `summary()` when reporting results. Do not claim a limit was applied without it.
5. Throughput cost at duty 0.6 measured at **0.80x** iterations per wall-clock second. Factor this into time estimates.
6. Long jobs must be launched as harness-tracked background tasks. A `nohup`'d process inside `wsl.exe -e bash -lc` **is killed when that shell exits**.

## Measured behaviour

Under a busy GPU (foreground desktop plus another job, `other_util` = 99%), `AdaptiveBudget` drove target duty to 0.15 and settled at a measured 0.171 over 74 iterations — 4.3 s busy against 20.8 s sleep.

Fixed throttle, 12 s synthetic load, user's desktop at an 85.3% baseline:

| our target | our measured duty | total GPU util |
|---|---|---|
| unthrottled | 1.000 | 98.2% |
| 0.6 | 0.595 | 87.9% |
| 0.4 | 0.406 | 85.5% |

Throttling to 0.6 cut our contribution above baseline from +12.9 points to +2.6.

## Interpreting nvidia-smi

`utilization.gpu` is the fraction of sampled time during which *any* kernel was resident — not SM occupancy. An 85% reading does not mean the card is 85% full, and two processes can each observe high utilization at once. Never present this number as a capacity share.
