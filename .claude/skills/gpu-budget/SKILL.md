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

## 更正（2026-08-25）：显存才是硬约束，占空比节流对它无能为力

上表「0.6 占空比 → 总利用率 87.9%」是在**显存宽裕**的条件下测的。
2026-08-25 在 LOTree 阶段一训练上照搬，失败：

| 观测 | 数值 |
|---|---|
| 进程级实测占空比 | 0.525 / 0.578（目标 0.60）—— 节流本身生效 |
| 我们**停止窗口内**采样的总利用率 | 中位数 100.0，最大 100.0 |
| 停止前显存 | 24060 / 24564 MiB |
| 杀掉我们全部进程后 | 利用率仍 98%，显存 4810 MiB |

三条结论：

1. **占空比节流让不出显存。** 进程活着就一直占着那 20 GB。用户体感到的
   「GPU 占用太高」在显存吃紧时主要来自显存，不是 SM 时间片。
   要限显存只有 `torch.cuda.set_per_process_memory_fraction`，
   **必须在进程启动时设定**——已经在跑的进程改不了，只能重启。
2. **卡已经被前台打满时，我们让出时间片也看不出效果。** 停止窗口内仍读到 100%，
   而杀光我们的进程后仍是 98%——那 98% 本来就不是我们的。
   此时唯一有意义的动作是**让出显存**或**整个停掉**。
3. **`utilization.gpu` 在这种场合没有诊断价值。** 它读 100% 既可能是我们，
   也可能是别人，还可能是残留 kernel。判断我们自己的贡献要看
   `memory.used` 在杀掉进程前后的差值——本次是 24060 → 4810 MiB。

### 追加规则

7. 启动长任务前先读一次 `memory.used`。若空闲显存不足 8 GB，**不要启动**，
   或以 `MemoryCap` 显式限额启动。
8. 报告节流效果时必须同时给出**杀掉进程前后的 `memory.used` 差值**，
   只报占空比是不够的——占空比达标而用户依然卡顿，本次就是实例。
9. 外部 SIGSTOP/SIGCONT 可以在不改代码的情况下对已在运行的进程做占空比节流
   （`scripts/extern_throttle.py`），但**注意 SIGSTOP 状态下的进程收不到 SIGTERM**，
   要先 SIGCONT 再终止，否则会以为杀掉了其实没有。
