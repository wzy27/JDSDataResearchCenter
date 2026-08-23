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

## GS-Octree 的脚本分工与旋钮实际形态

各训练脚本对外部 `LOTree-zhengyu` 的依赖：

| 脚本 | LOTree/svox 依赖 | 行数 | 含 hessian |
|---|---:|---:|---|
| `train-origin.py` | 0 | 352 | 否（纯 3DGS 基线） |
| `train-base.py` | 0 | — | 否 |
| `train-octree.py` | 1 | 448 | 否 |
| **`train-big.py`** | **3** | **774** | **是** |

**论文的完整方法在 `train-big.py`**，`hessian_eikonal` 仅在此实现。三个基线脚本不依赖外部仓库，**可在无 `LOTree-zhengyu` 的情况下运行**，这为 E-α 的「仅表示 B（纯 3DGS）」一路提供了可立即执行的对照。

### 旋钮三的实际形态：不是退火曲线，是硬编码常数

`train-big.py` 中 Hessian/Eikonal 的调用：

```python
octree.SampleGaussianPoints(gaussian_sigma=0.1, max_n_samples=64, gauss_sampling=False)
...
scale_hess = 1e-12
scale_eiko = 1e-6
octree.VolumePointsHessEikon(
    hessian_on=True, eikonal_on=True,
    scale_h=scale_hess, scale_e=scale_eiko,
    eikon_thres_min=0.8, eikon_thres_max=1.5, ...)
```

立论文档原先记为「singular-Hessian 退火权重」，依据是 Wang et al. 原文的 annealing 描述。**实际实现中并无退火，而是两个硬编码常数**，且 `scale_hess` 与 `scale_eiko` 相差六个数量级——二者的相对比例直接决定 Hessian 项与 Eikonal 项谁主导优化。

`eikon_thres_min=0.8` / `eikon_thres_max=1.5` 为梯度范数的容许区间，同样硬编码。
`gaussian_sigma=0.1` 与 `max_n_samples=64` 决定从 Gaussian 采样多少点用于计算高阶导数。

**因此 E-γ 需扫描的是这六个常数，而非一条退火曲线。** 立论文档中该处表述已据此修正。

### 阻塞状态更新

- `train-big.py` 需 `LOctree`、`LOTreeOptGS`、`svox` —— 前两者在未公开的 `LOTree-zhengyu`；`svox` 为 PlenOctrees 开源库，可 pip 安装。
- `train-origin.py` 等基线脚本无此依赖，**可先行验证**。

---

## 编译过程中发现的上游缺陷

`sub/diff-surfel-rasterization/cuda_rasterizer/backward.cu` 无法编译：

```
backward.cu(695): error: no instance of function template "preprocessCUDA" matches the argument list
```

原因：`preprocessCUDA` 的模板声明（第 534–560 行）含 25 个形参，其中第 540 行为

```cpp
const float* ref_shs,
```

而第 695 行的调用只传 24 个实参，缺少 `ref_shs`。

**`ref_shs` 在整个 `backward.cu` 中仅出现这一次**——既未被函数体使用，也未被任何调用方传入。这是作者在原版 2DGS 的 `diff-surfel-rasterization` 上改造时留下的死参数。

处理：删除该行后编译通过。原文件备份为 `backward.cu.orig`。该修改不改变任何计算，仅移除未使用的形参。

### 这一发现与论点的关系

它本身是个小缺陷，但说明一件与本项目论点直接相关的事：**MGSR 公开的这份代码，其 2DGS 分支的 backward 从未被成功编译过**——若编译过，此错误必然暴露。

这引出两个必须核实的问题：

1. 论文实验所用的代码与公开的这份是否一致？
2. 若公开版本与实验版本存在差异，则依据公开代码所做的任何旋钮分析，其结论未必适用于论文数值。

**在核实之前，不得把基于此代码的实验结果与论文报告的数值直接比较。** 该项须联系作者确认，或通过复现论文数值来间接验证。

这也强化了 P0 中「代码能否复现论文数值」这一前置任务的必要性——它不只是工程步骤，而是后续所有分析的有效性前提。

---

## 环境搭建的完整记录（可复现）

两个仓库共用一个 conda 环境 `MGSR`（python 3.11 + torch 2.0.1+cu118），CUDA 工具链
复用 `drivestudio` 环境的 nvcc 11.8 与 gcc 11。

### 必须的修正

| 问题 | 原因 | 处理 |
|---|---|---|
| 首次编译全部失败 | `git clone --depth 1` 不拉子模块 | `git submodule update --init --recursive` |
| pip 装到错误环境 | `export PATH=$CUDA_HOME/bin:$PATH` 把 `drivestudio` 置于 `MGSR` 之前 | 改为 `PATH=$CONDA_PREFIX/bin:$PATH:$CUDA_HOME/bin` |
| `glm/glm.hpp: No such file` | rasterizer 自身的 `third_party/glm` 未随递归拉取到位 | 从上游 clone `g-truc/glm@0.9.9.8` 并复制到三处 `third_party/glm` |
| `pkg_resources` 缺失 | 新 setuptools 移除了该模块 | `pip install "setuptools<70"` |
| `RuntimeError: Numpy is not available` | torch 2.0.1 针对 numpy 1.x 编译，环境为 numpy 2.4 | `pip install "numpy<2"`，并将 opencv 降至 4.8.1.78、plyfile 降至 1.1.2 |
| GS-Octree `No url found for submodule path 'submodules/simple-kNN'` | `.gitmodules` 中路径大小写为 `simple-kNN`，实际目录为 `simple-knn` | 直接从 `gitlab.inria.fr/bkerbl/simple-knn` clone |

前五项为本地操作或依赖漂移问题；最后一项为 GS-Octree 仓库自身的不一致。

### 验证结果

- MGSR：`diff_surfel_rasterization`、`simple_knn`、`diff_gaussian_rasterization` 三个 CUDA 扩展全部编译通过并可导入。
- GS-Octree：基线所需模块（`scene`、`gaussian_renderer`、`simple_knn`、`diff_gaussian_rasterization`）可导入；完整方法仍阻塞于 `LOTree-zhengyu`。

### 数据

`tandt_db.zip`（650 MB，3DGS 官方，无需授权）已下载并解包，含 `tandt/truck`、`tandt/train`、`db/drjohnson`、`db/playroom`，均为 COLMAP 标准格式。

**用于管线验证而非论文对比**——MGSR 的论文实验使用 DTU 与 OmniObject3D，GS-Octree 的默认脚本亦使用 DTU（`scan40`）。两者数据集重合，这对 E-α 的公平对比有利；正式实验须换用 DTU。
