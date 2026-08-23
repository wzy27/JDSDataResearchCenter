# 计划版本日志

## 2026-08-18 — v1（当前）

- 从 Presentation 与 QE report 固化 FastRelight 的范围、组件、监督和评估锚点。
- 将当前阶段纠正为“总体设计完成，完整实现和规模验证未完成”。
- 首版输入锁定为 RGB + LiDAR；radar 延后到数据和收益明确后再决策。
- 建立 P0–P6、G0–G6 阶段门，优先得到可复现组件 baseline 和 CARLA 光照真值，而不是直接联合训练。
- 新增三条可证伪 IDEA、稳定 TASK ID 和 planned/blocked 实验记录。
- 锁定 DriveStudio `main@e59bda4f` 与 Humans4D 子模块，建立 sequence manifest schema；因缺 Linux/NVIDIA executor 和 Waymo 数据，P0 smoke 仍 blocked。
- 竞争检索确认 LightSim、DrivingGaussian++、MADrive、HorizonForge、DrivingEditor 等已覆盖总体目标；主方法收缩为动态跨组件 visibility/shadow transport。

后续版本不覆盖本文件对应计划；只有 baseline 复现结果、传感器决策或阶段门结论变化时才新增版本。

## 2026-08-23 — 范围收缩至观测受限条件下的驾驶场景行人重建

触发：导师要求成果必须落在重建方向；确认一位专攻人体与衣物重建的合作者；主研究者强项为 3DGS 重建。

调研结论（见 `sources/2026-08-23_reconstruction_pivot_landscape.md` 与 `sources/2026-08-23_pedestrian_reconstruction_sota_survey.md`）：

- 「可编辑 + 可重打光驾驶场景」整体已被 LightSim、DrivingGaussian++、MADrive、HorizonForge 占据。
- 共享环境光加空间光照残差被 CVPR 2026 Illumination-Consistent Human-Scene Reconstruction 占据；`IDEA-DC38D8C3CC41` 标记 `challenged`。
- 动态作为逆渲染监督被 LumiMotion 占据；驾驶场景 BRDF 分解被 Nighttime PBR-GS 占据；自建 CARLA paired-light 基准被 ReLumix 的 CARLA Relight 占据。
- 衣物解耦被 CLOTH-HUGS 占据，不能作为主创新。
- 剩余空间为 human-region 的度量空白：OmniRe 的 28.15/24.36 PSNR 至今未被公开超越，后续方法只报整场景聚合指标。

新方向定位为 **OmniRe 人体分支的改进工作**，非新方向。主创新落在观测受限条件下的重建，属 3DGS/几何/多传感器/评测范畴。

原 P0–P6 路线与 G0–G6 阶段门不再适用；`EXP-1584B0636795`、`EXP-4C2A9AD4C3D2`、`EXP-54CD8F9137F2`、`EXP-C4E8F5217892` 保留为历史记录。
