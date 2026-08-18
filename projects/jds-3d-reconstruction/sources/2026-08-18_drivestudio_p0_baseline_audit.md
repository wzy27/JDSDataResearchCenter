# P0：DriveStudio 最新版基线锁定与静态审计

## 锁定结果

- 上游：`https://github.com/ziyc/drivestudio.git`
- 默认分支：`main`
- 2026-08-18 查询到的 HEAD：`e59bda4fa681f829dbb1d65f0de582b0f633c450`
- commit 时间：2025-08-27 16:42:36 +08:00，message `update`
- license：MIT
- 子模块：`third_party/Humans4D@6ec79656a23c33237c724742ca2a0ec00b398b53`
- 机器外部 checkout：逻辑 connection `drivestudio-upstream`；源码不复制进本仓库。

固定配置与 hash 见 [`../codebases/manifest.yaml`](../codebases/manifest.yaml)。

## 代码能力映射

| FastRelight 组件 | DriveStudio 对应实现 | P0 判断 |
|---|---|---|
| 静态背景 | `Background: VanillaGaussians`，LiDAR 初始化 | 已有 baseline 实现 |
| 刚性车辆 | `RigidNodes`，canonical Gaussians + instance R/T | 已有 baseline 实现 |
| 行人 | `SMPLNodes`，SMPL/LBS/voxel deformer | 已有 baseline 实现，但依赖 SMPL model 与 humanpose |
| 通用形变体 | `DeformableNodes` | 已有 baseline 实现 |
| 天空 | `Sky: EnvLight` | 已有可学习天空环境纹理；不是可控物理光照 |
| 曝光 | `AffineTransform` | 有相机外观补偿；需防止它吸收场景光照 |
| 重打光 | 无统一 material/light/visibility 接口 | FastRelight 必须新增 |

评估路径在非训练模式下已支持分层输出：`Background_*`、`RigidNodes_*`、`DeformableNodes_*`、`SMPLNodes_*`、`rgb_sky`、composite RGB；这可直接作为 G0 五类组件 contract 的底座。

## 上游官方运行合约

- Python 3.9；PyTorch 2.0.0 + CUDA 11.7；gsplat 1.3.0；PyTorch3D；nvdiffrast；SMPLX editable install。
- Waymo 默认 3 cameras，processed data 包括 images、LiDAR、ego pose、标定、sky/dynamic masks、instances 和可选 humanpose。
- 官方 `configs/omnire.yaml` 为 30k iterations；paper reproduction 使用 `configs/paper_legacy/omnire.yaml`。
- 推荐训练命令从 `tools/train.py --config_file configs/omnire.yaml ... dataset=waymo/3cams` 进入；评估从 `tools/eval.py --resume_from <checkpoint>` 进入。

## 当前执行器事实

本次只做了只读/静态 P0：clone、submodule、commit/license/config hash、组件和输出路径审计。当前 Windows 工作机：

- `python 3.10.11`，不是上游锁定的 3.9；
- 未发现 `conda`；
- 未发现 `nvidia-smi`，没有可验证 NVIDIA/CUDA executor；
- 未发现本地 `waymo/raw` 或 `waymo/processed` 数据；
- S3 的 JDS 归档不是标准 Waymo processed dataset。

因此 `EXP-54CD8F9137F2` 仍为 `blocked`。解除条件是：提供 Linux + NVIDIA executor connection，建立 Python 3.9/CUDA 11.7 环境，选择有车辆/行人且许可明确的 Waymo 8–16 帧 smoke scene，完成数据 manifest/hash。

## P0 新增的数据合约

- [`../datasets/sequence_manifest.schema.json`](../datasets/sequence_manifest.schema.json)：序列、传感器、五类组件、光照和 provenance 的最小 schema。
- [`../datasets/smoke_waymo.example.json`](../datasets/smoke_waymo.example.json)：未解析字段保持 `null`/`UNRESOLVED`，不猜 scene ID、坐标或数据版本。

## 与 FastRelight 的直接技术缺口

DriveStudio 的 SH/EnvLight/Affine 是 appearance reconstruction 工具，不等同于材质—照明分解。FastRelight 需要在其上新增：linear-RGB/相机成像边界、跨组件共享光照、材质恒定约束、动态 cast/receive visibility、编辑 manifest 和 CARLA paired-light evaluator。
