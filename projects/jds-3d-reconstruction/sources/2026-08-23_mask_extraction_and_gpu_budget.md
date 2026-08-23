# 2026-08-23 掩码生成的实现偏离与 GPU 预算控制

## 1. sky mask：上游实现在本机不可运行

上游 `datasets/tools/extract_masks.py` 依赖 `mmcv-full==1.2.7`，后者要求 `pytorch<1.9`，官方指引为 `torch 1.8.1+cu111` 的独立 conda 环境。

**cu111 最高支持 sm_86，RTX 4090 为 sm_89，该环境在本机无法运行。** 这与先前 CUDA 11.7 无法编译扩展是同一类问题：上游锁定的工具链早于 Ada 架构。

### 采用的替代实现

改用同一权重的 HuggingFace 版本 `nvidia/segformer-b5-finetuned-cityscapes-1024-1024`，配合本环境的 `torch 2.0.0+cu118` 与 `transformers 4.36.2`。

输出格式与上游严格一致：

| 输出 | 定义 |
|---|---|
| `sky_masks/{base}.png` | `(class == 10) * 255` |
| `fine_dynamic_masks/human/{base}.png` | `(class ∈ {11,12,17,18}) AND rough_human` |
| `fine_dynamic_masks/vehicle/{base}.png` | `(class ∈ {13,14,15}) AND rough_vehicle` |
| `fine_dynamic_masks/all/{base}.png` | `human OR vehicle` |

类别索引与上游 `semantic_classes` 列表逐项核对一致；运行时断言 `id2label[10] == "sky"`。

### 验证

在 scene 004 的 3 张图上核对：

| 图 | 天空占比 | 上/中/下三分带 | 天空亮度 | 非天空亮度 |
|---|---:|---|---:|---:|
| 000_0 | 8.0% | 22.9 / 1.2 / 0.0 | 199.1 | 105.7 |
| 001_0 | 8.1% | 23.0 / 1.3 / 0.0 | 200.0 | 105.5 |
| 002_0 | 8.1% | 22.9 / 1.3 / 0.0 | 200.3 | 105.0 |

掩码尺寸与原图一致；天空集中于上三分带且亮度显著高于非天空。三项断言通过。

**这只验证了输出合理，未与上游 mmseg 实现做逐像素比对**——后者在本机无法运行，因此该比对无法进行。两种实现使用同一权重，但预处理（resize、归一化）与推理时的滑窗策略可能不同，掩码边界存在差异的可能性无法排除。此项作为已知风险记录。

## 2. GPU 预算控制

### 本机可用手段的实测边界

| 手段 | 状态 | 依据 |
|---|---|---|
| MIG 硬件分区 | 不可用 | GeForce 不支持，`mig.mode.current` 返回 `[N/A]` |
| MPS 限制 SM 份额 | 不可用 | `nvidia-cuda-mps-control` 不存在；WSL2 不支持 MPS |
| 功耗限制 / 计算模式 | 不可用 | `nvidia-smi -pl` 返回 `Insufficient Permissions`，驱动在 Windows 侧 |
| 逐进程 GPU 归属 | 不可用 | `--query-compute-apps` 与 `pmon` 在 WSL 内均返回空 |
| 单进程显存上限 | **可用** | `torch.cuda.set_per_process_memory_fraction`，超额分配被 OOM 拦截 |
| 占空比节流 | **可用** | 目标 0.6 实测 0.595；目标 0.4 实测 0.406 |

**结论：本机无法做 GPU 分区或抢占，只能做协作式退让。** 本进程主动缩小自己，无法保证任何整卡利用率数值。

### 自适应退让的实现要点

逐进程归属不可用，因此前台负载无法直接查询。采用的观测是：

> 在本进程节流休眠的窗口内采样到的整卡利用率，即为其他进程的负载。

据此按策略动态调整目标占空比（他人负载 <25% → 0.85；25–50% → 0.60；50–75% → 0.35；≥75% → 0.15），并在空闲显存低于阈值时进一步压到 0.15。

实测：在整卡 99% 负载下，控制器把目标压到 0.15，74 轮实测占空比 0.171（忙 4.3 s / 睡 20.8 s）。

### 过程中发现并修复的缺陷

首次运行掩码提取时报告 `duty=0.875`，远高于 0.6 的目标。原因是 `DutyThrottle` 的 `max_sleep` 默认 0.25 s，而 batch=4 时每轮 GPU 工作约 2 s，所需休眠约 1.3 s 被硬截断。

修复：上限放宽至 2.0 s，并在 `summary()` 中增加 `clamped_iterations` 与 `clamp_warning`，使截断不再静默发生。同时将每轮工作量控制在建议区间（batch=1）。

**这个缺陷的性质值得记录：节流器会报告一个看似正常的占空比，而实际限制根本没有达到目标。若未核对日志中的 duty 数值，会误以为限制已生效。** 因此规定：凡声称施加了 GPU 限制，必须同时给出 `summary()` 的实测值。

### 代价

目标占空比 0.6 时，相同墙钟时间内的迭代数为不限制时的 **0.80x**。

## 3. 沉淀

上述控制逻辑已固化为 Claude Code skill `gpu-budget`，位于工作区 `.claude/skills/gpu-budget/`，含 `gpu_budget.py`（固定节流）与 `adaptive_budget.py`（自适应退让）两个模块及使用规则。

## 4. 待办

- 三个行人密集场景（000/001/008）的 sky mask 与 fine dynamic mask 生成中。
- 其余 7 个场景暂未生成；`TASK-91DA4E6C0F` 在三场景完成后即可解除对 `EXP-D364146FE7A6` 的阻塞（该实验只需行人密集场景）。
- 分层评测器当前使用 `dynamic_masks/human`（3D box 投影，较粗）；`fine_dynamic_masks/human` 生成后应切换过去并重跑自测。
