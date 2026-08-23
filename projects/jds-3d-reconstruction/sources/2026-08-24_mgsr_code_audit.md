# 2026-08-24 MGSR 代码审计：互导循环的三个旋钮

> 目的：把立论文档中「三个手工旋钮」从论文表述落实到代码位置，为 E-γ 提供可操作对象。
> 代码：`github.com/TsingyuanChou/MGSR`，clone 于 2026-08-24，最后 push 2026-02-19。

## 1. 三阶段结构

`train.py` 定义三个训练入口：

| 函数 | 作用 |
|---|---|
| `training_geo_2d` | 2DGS 分支独立 warm-up |
| `training_ref_3d` | 3DGS 分支独立 warm-up |
| `training_geo_ref` | 互导阶段，两支交替优化 |

两支各自 warm-up 至触发 early-stop 后，才进入互导。

## 2. 旋钮一：warm-up 何时结束

两支的 early-stop 判据完全相同：

```python
if iteration > opt.early_stop_until_iter:
    loss_window.append(total_loss.item())
    if len(loss_window) == opt.loss_window_size:
        changed = max(loss_window) - min(loss_window)
        if changed < opt.threshold:
            print("Geo stopped at {} iters.")
```

即：**在滑动窗口内损失的极差小于阈值即判定收敛并停止**。

三个超参：`early_stop_until_iter`（最早允许停的迭代）、`loss_window_size`（窗口长度）、`threshold`（极差阈值）。

**这是纯损失域的收敛代理，不涉及几何。** 它决定了每支带着什么状态进入互导循环——若一支停得过早，携带未收敛的几何进入互导，另一支将去拟合该错误几何。这正是假设 H1 所指的误差放大路径，且现在有了可直接操作的入口。

## 3. 旋钮二：损失权重的启用点

```python
lambda_normal = opt.lambda_normal if iteration > 7000 else 0.0
lambda_dist   = opt.lambda_normal if iteration > 3000 else 0.0
```

7000 与 3000 为硬编码魔数，继承自 2DGS。

**需要核实的一处**：第二行右侧使用的是 `opt.lambda_normal` 而非 `opt.lambda_dist`。原版 2DGS 对应位置为 `opt.lambda_dist`。二者可能有意合并，也可能是转写笔误。**在未与作者确认前，不得作为缺陷陈述**；但若为笔误，则意味着 distortion 项实际使用了 normal 项的权重，会直接影响几何结果，且是 E-γ 扫描时必须固定的变量。

## 4. 旋钮三：致密化与不透明度重置

```python
size_threshold = 20 if iteration > opt.geo_opacity_reset_interval else None
if iteration > opt.geo_densify_from_iter and iteration % opt.geo_densification_interval == 0:
```

`size_threshold = 20` 为魔数。致密化区间、不透明度重置间隔均为超参，geo 与 ref 两支各有一套。

## 5. 对 E-γ 的影响

原计划扫描的三个旋钮中，「warm-up 与切换时机」现细化为三个可扫描超参（`early_stop_until_iter`、`loss_window_size`、`threshold`），且其判据的性质已明确——**损失域代理而非几何域判据**，这本身即为一个可检验的设计选择：

> 以损失极差判定收敛，是否足以保证进入互导的几何已经可靠？

该问法比笼统的「warm-up 时机是启发式的」更具体，且可直接实验：在同一场景上改变 early-stop 阈值，观察进入互导时的几何误差与最终结果的关系。

## 6. 尚未核实

- MGSR 代码能否复现论文数值（环境安装中）。
- `lambda_dist` 一行是否为笔误，需与原版 2DGS 逐行比对并考虑联系作者。
- GS-Octree 的代码未公开检索到；`cskrren/GSOctree` 是 city-super 的 Octree-GS 复现，与本工作无关。**GS-Octree 代码须由研究者提供。**

---

# 补充：GS-Octree 代码状态（2026-08-24）

代码位于 `github.com/wzy27/gaussian-splatting`（研究者本人仓库，非 fork）。

## 分支

| 分支 | 最后提交 | 说明 |
|---|---|---|
| `final` | 2024-07-22 `save final work version` | **论文对应版本**，相对 `main` 有 46 文件 / 4546 行改动 |
| `public` / `public-1` | 2024-07-22 | 清理脚本与未用参数 |
| `main` | 2024-01-24 | 早期 |
| `debug` | 2024-03-05 | |

关键文件：`train-octree.py`、`train-big.py`、`train-base.py`、`octree_train.sh`、`threshold_train.sh`。

## 阻塞：核心依赖不在该仓库内

`train-octree.py` 的导入：

```python
from LOctree import LOctreeA
```

`train-big.py` 另有：

```python
from svox import utils
from LOTreeOptGS import InitialFlags, tree_image_eval
```

而所有训练脚本均包含：

```bash
export PYTHONPATH=$PYTHONPATH:/data/nglm005/zhengyu.wen/LOTree-zhengyu
```

即**八叉树 SDF 的核心实现位于独立仓库 `LOTree-zhengyu`，该仓库未在 GitHub 公开检索到**。没有它，GS-Octree 无法运行。

`svox` 为 PlenOctrees 的开源库，可安装；但 `LOctree` / `LOTreeOptGS` 为本项目自有代码。

**该项须由研究者提供。** 需要的是 `LOTree-zhengyu` 仓库或其打包，以及与 `final` 分支配套的版本。

## 已知的默认参数（`octree_train.sh`）

```
--iterations 30000  --lambda_opacity 3  --lambda_orientation 0
--lambda_scale 0.1  --opacity_scalar 200  --near_threshold 0.01  -w
# --hessian_eikonal        <- 在脚本中被注释掉
```

注意 `--hessian_eikonal` 在默认脚本中处于注释状态，说明 singular-Hessian 项并非默认开启，而是可选开关。**这对 E-γ 有直接影响**：该项的开关本身即为一个旋钮，且论文中它是被强调的贡献之一，实际默认脚本却未启用——需要与研究者确认论文实验用的是哪一档。
