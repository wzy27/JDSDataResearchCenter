# 2026-08-23 执行器登记与上游环境构建

## 执行器

2026-08-18 的 P0 审计把 `EXP-54CD8F9137F2` 标为 `blocked`，原因之一是 `EXECUTOR_UNAVAILABLE`。该条件现已解除。

| 项 | 值 |
|---|---|
| executor_id | `wsl2-ubuntu2404-rtx4090` |
| 宿主 | Windows 11 Pro 26200 + WSL2 |
| 发行版 | Ubuntu 24.04.1 LTS，内核 6.18.33.2-microsoft-standard-WSL2 |
| GPU | NVIDIA GeForce RTX 4090，24 GB，compute capability 8.9 |
| 驱动 | 591.86（NVIDIA-SMI 590.57） |
| CPU / 内存 | 16 核 / 30 GB |
| 可用磁盘 | WSL ext4 根分区 690 GB |

机器本地映射写入 gitignore 的 `.researchcenter.local.json`，不进入 Git。

`waymo-smoke-data` 仍为 `UNRESOLVED`，因此 `EXP-54CD8F9137F2` 的 `DATA_UNPINNED` 阻塞未解除。

## 上游 checkout

- `drivestudio-upstream` → `/home/wzy27/fastrelight/drivestudio`
- `git rev-parse HEAD` = `e59bda4fa681f829dbb1d65f0de582b0f633c450`，与 `codebases/manifest.yaml` 锁定值一致
- `third_party/Humans4D` = `6ec79656a23c33237c724742ca2a0ec00b398b53`，与锁定值一致

## 与上游锁定环境的偏离

上游 `requirements.txt` 与 README 锁定 Python 3.9 + CUDA 11.7 + torch 2.0.0+cu117。实际构建有三处偏离，均已验证并记录原因：

| 项 | 上游 | 本机 | 原因 |
|---|---|---|---|
| CUDA | 11.7 | **11.8** | CUDA 11.7 的 nvcc 最高支持 sm_87，不认识 RTX 4090 的 sm_89。11.8 是原生支持 Ada 的最低版本，且 torch 2.0.0 有对应 cu118 轮子，属最小偏离 |
| torch / torchvision | 2.0.0+cu117 / 0.15.0+cu117 | 2.0.0+cu118 / 0.15.1+cu118 | 跟随 CUDA 11.8；torch 版本号不变，torchvision 0.15.1 是与 torch 2.0.0 配套的版本 |
| xformers | 0.0.18（cu117 构建） | **移除** | 全仓库 `grep -rn "xformers" --include=*.py` 无任何 import，属失效 pin。保留会与 cu118 冲突 |

编译扩展时另需 `TORCH_CUDA_ARCH_LIST=8.9`，并使用 conda-forge 的 gcc/g++ 11：Ubuntu 24.04 默认 gcc 13，CUDA 11.8 的 `crt/host_config.h` 硬拒绝 gcc > 11，直接编译会失败于 `unsupported GNU version`。未使用 `-allow-unsupported-compiler` 绕过。

## 扩展编译

四个 CUDA/渲染扩展全部构建成功，均以 `TORCH_CUDA_ARCH_LIST=8.9` 和 conda gcc/g++ 11.4 编译：

| 扩展 | 版本 | 备注 |
|---|---|---|
| gsplat | 1.3.0 | 从源码编译，`__CUDA_ARCH_LIST__=890` |
| pytorch3d | 0.7.8 | `@stable` 分支源码编译 |
| nvdiffrast | 0.4.0 | 必须加 `--no-build-isolation`，否则构建环境中无 torch，报 `Cannot compile nvdiffrast CUDA extension` |
| smplx | 0.1.28 | `third_party/smplx` editable 安装 |

## 验证

Python 3.9.23，`nvcc` 11.8.89。完整 import 与内核冒烟测试（仅 16 个 Gaussian 渲染到 64x64，不构成显卡负载）：

```
torch       2.0.0+cu118 | cuda 11.8 | avail True
device      NVIDIA GeForce RTX 4090 cc (8, 9)
gsplat      1.3.0
pytorch3d   0.7.8
smplx       0.1.28
nvdiffrast  nvdiffrast.torch ok
--- drivestudio component modules ---
SMPLNodes / RigidNodes / DeformableNodes / VanillaGaussians / EnvLight / AffineTransform  OK
--- gsplat CUDA kernel smoke (tiny) ---
rasterization ok, out (1, 64, 64, 3)
```

五类组件对应的上游模块与 `EnvLight`/`AffineTransform` 均可导入，gsplat 的 CUDA rasterization kernel 在 sm_89 上实际执行成功。这证明工具链可用，不证明任何重建质量结论。

`requirements.txt`（去掉上述三项后）全部安装成功，含 numpy 1.23.1、open3d 0.16.0、viser 0.2.1、nerfview 0.0.3。

## 复现方式

构建脚本保存在执行器本地 `~/fastrelight/setup_deps.sh` 与 `~/fastrelight/setup_ext.sh`，不进入 Git（含机器绝对路径）。

## 仍未完成

- 未下载 Waymo raw/processed 数据，未选定 8-16 帧 smoke 序列，未建立数据 manifest。`EXP-54CD8F9137F2` 的 `DATA_UNPINNED` 阻塞保持。
- 未获取 SMPL/SMPL-X model 文件与 humanpose 预处理产物。
- 未执行任何训练或渲染，未产生任何指标。
