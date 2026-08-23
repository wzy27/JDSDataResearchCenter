# 观测受限条件下的驾驶场景行人重建

## 研究问题

驾驶采集条件对人体重建造成的观测不足是结构性的：远距离行人在图像中可能仅数十像素高，rig 相机之间重叠低，单个行人的观测窗口短，相机自身在运动，行人之间相互遮挡。受控条件下的着衣人体重建方法全部预设了相反的观测条件——被摄者占据画面主体、分辨率高、帧数充足、相机绕人运动。

> **在观测严重不足的驾驶采集条件下，如何把人重建出来？**

方法侧重点是观测充分性建模、跨相机与跨时刻的观测聚合，以及针对该问题的分层评测；人体与衣物先验（SMPL/LBS、LHM 类前馈模型）作为被调用模块，不作为方法主创新。

## 定位（必须如实表述）

**本方向不是新方向，是 OmniRe 人体分支的改进工作。** 相关证据与竞争分析见 [`sources/2026-08-23_pedestrian_reconstruction_sota_survey.md`](sources/2026-08-23_pedestrian_reconstruction_sota_survey.md)。

支撑该方向成立的三点：

1. **human-region 存在度量空白。** OmniRe 报告 human region 重建 28.15 PSNR / 0.845 SSIM、NVS 24.36 / 0.727，至今未被公开超越——不是无人做得更好，而是后续方法（含整体更强的 DriveSplat）只报整场景聚合指标，行人像素在其中被完全稀释。
2. **瓶颈有双重背书。** 综述 `LIT-334F00637EB0` 就行人重建点名 *Degradation at Long Range* 与 *Complex Occlusions*；OmniRe 自身在 §4.2 承认远距/遮挡行人的姿态预测失准。
3. **剩余空间落在 3DGS/几何侧。** 衣物解耦已被 CLOTH-HUGS（`LIT-8B84FE3C3F97`）占据，不能作为主创新；而观测条件问题属于表示、标定、多传感器与评测范畴。

**风险：** 需要在 human-region 上取得大幅度提升，小数点级改善不足以支撑。若分层测量显示 OmniRe 在各层均已足够好，方向不成立。

## 当前阶段

P0：分层 human-region 基线测量，见 [`EXP-D364146FE7A6`](experiments/records/EXP-D364146FE7A6.json)。这是选题的 go/no-go 前置判据，在其结论产出前不进入方法设计。

| 判据 | 结论 |
|---|---|
| 远距/高遮挡分层显著塌陷 | 方向成立，该分层表即论文首图 |
| 各层均接近整体水平 | 立即换题 |

## 数据与基线

- 基线：DriveStudio / OmniRe，锁定 `main@e59bda4fa681f829dbb1d65f0de582b0f633c450`，见 [`codebases/manifest.yaml`](codebases/manifest.yaml)。
- 数据：nuScenes v1.0-mini（10 场景，其中 5 个标注含大量行人）。选择理由是规模小、DriveStudio 官方示例即用它、且官方提供预处理人体姿态，可跳过 4D-Humans 流水线。
- 执行器：`wsl2-ubuntu2404-rtx4090`，环境构建与偏离见 [`sources/2026-08-23_executor_environment_build.md`](sources/2026-08-23_executor_environment_build.md)。

## 项目入口

- [`TODO.md`](TODO.md)：带稳定 TASK ID 的执行视图。
- [`sources/2026-08-23_pedestrian_reconstruction_sota_survey.md`](sources/2026-08-23_pedestrian_reconstruction_sota_survey.md)：SOTA 地图、剩余空间与定位。
- [`sources/2026-08-23_reconstruction_pivot_landscape.md`](sources/2026-08-23_reconstruction_pivot_landscape.md)：转向重建方向时的竞争格局。
- [`ideas/records/IDEA-F1BED52F1B2D.json`](ideas/records/IDEA-F1BED52F1B2D.json)：当前主 idea 及其演化史。
- [`progress.md`](progress.md)：既有资产审计。

## 与先前 FastRelight 范围的关系

本项目原为 FastRelight（可编辑、可重打光的 4D 驾驶场景重建）。2026-08-23 收缩为上述行人重建方向，原因记录在 [`plans/CHANGELOG.md`](plans/CHANGELOG.md)：

- 「可编辑 + 可重打光驾驶场景」整体已被 LightSim、DrivingGaussian++、MADrive、HorizonForge 等占据；
- 共享环境光加空间光照残差被 CVPR 2026 人体—场景联合重建工作占据（`IDEA-DC38D8C3CC41` 已标记 `challenged`）；
- 导师要求成果必须落在重建方向，而重打光/阴影传递属渲染贡献。

原 [`plans/2026-08-18_fastrelight_research_program_v1.md`](plans/2026-08-18_fastrelight_research_program_v1.md) 及 `EXP-1584B0636795`、`EXP-4C2A9AD4C3D2`、`EXP-54CD8F9137F2`、`EXP-C4E8F5217892` 保留为历史记录，不再作为当前主线。

## 仓库边界

原始文档、S3 数据、视频、数据集、模型权重和训练输出不进入 Git。完成项必须能追溯到代码 commit、数据 manifest、命令、环境、指标和产物；只有架构图、文件名或渲染视频不能标记为「已完成」。
