# FastRelight 直接竞争格局（2026-08-18）

> 检索范围：动态驾驶场景 3D/4DGS 重建、对象级编辑、feed-forward reconstruction、材质/光照分解、动态对象阴影。结论基于论文全文可访问部分、官方摘要/项目页；文献台账区分 abstract-only 与 full-text inspected。

## 结论先行

当前 FastRelight 的总体目标已有强直接竞争，不能主张“首个可编辑、可重打光的驾驶场景系统”。最直接的先例是 LightSim；2025–2026 年的工作又分别占据了组件化编辑、feed-forward 4DGS、车辆资产重打光、视频扩散编辑和 Gaussian 阴影传递。

仍可能成立、但必须实验验证的差异化交叉点是：

> 在同一驾驶 4D Gaussian scene graph 中，让静态背景、刚体车辆、骨骼行人和通用形变体共享可审计的材质—光照—可见性合约，并在对象轨迹/姿态编辑后进行时间一致的跨组件 cast/receive shadow 传递；同时将重建摊销到 feed-forward 模型，并用 CARLA paired-light 真值验证。

这是一组交叉能力，不会自动构成论文贡献。主方法必须收敛为一个可证伪的技术核心，建议优先“动态跨组件 Gaussian visibility/shadow transport”，而不是泛化的 segmented lighting MLP。

## 直接竞争分层

| 强度 | 工作 | 已占据的能力 | 对 FastRelight 的影响 |
|---|---|---|---|
| 极高 | LightSim, NeurIPS 2023, arXiv:2312.06654 | 驾驶数字孪生；动态 actor/静态背景；插入/修改/移除；太阳、环境光和阴影重打光；时序视频 | 否定“editable + relightable driving scenes”总体新颖性；必须作为主 baseline |
| 极高 | DrivingGaussian++, arXiv:2508.20965 / TPAMI 2026 | LiDAR + 静态背景/动态对象 Gaussian graph；training-free 对象、纹理、天气编辑 | 组件化重建与编辑不是新贡献；需要证明光照物理性而非 weather style transfer |
| 极高 | MADrive, arXiv:2506.21520 / CVPR 2026 Findings | 70K 车辆资产记忆；relightable 2DGS 车辆替换、方向/尺度对齐和场景光照适配 | 车辆替换+重打光已被覆盖；FastRelight 必须比较完整资产、未观测面和投影阴影 |
| 高 | DrivingEditor, TIP 2026, DOI 10.1109/TIP.2026.3659733 | 4D composite GS；动态前景/静态背景双分支；无需 3D box 的编辑 | 前景/背景分解与编辑 claim 被进一步压缩 |
| 高 | HorizonForge, CVPR 2026, arXiv:2602.21333 | editable GS+mesh；任意车辆/轨迹；video diffusion 保时序；HorizonSuite benchmark | 纯几何编辑很难赢视觉真实感；需比较 diffusion refinement 或清晰强调物理/多视角一致性 |
| 高 | DrivingRecon, NeurIPS 2025, arXiv:2412.09043 | surround-view 到 4D Gaussian 的单次 feed-forward；静/动态解耦；scene editing | “feed-forward 4DGS for driving”不是新贡献，只能作为重建前端/对比 |
| 高 | DynamicVGGT, CVPR 2026, arXiv:2603.08254 | feed-forward dynamic point maps、future point、scene-flow 监督和 3DGS head | 进一步否定通用 feed-forward 动态重建 claim；应考虑复用而非重造前端 |
| 中高 | GS-ID, ICCV 2025, arXiv:2408.08524 | environment map + 空间变化 SGM lights + diffusion material priors + per-splat shadow direction | QE 中“环境光+segmented lighting+material prior”过于相似，不能作为核心新方法 |
| 中高 | Animated 3DGS Avatars..., arXiv:2601.01660 | Deep Gaussian Shadow Maps；SH HDRI probe；动态 avatar/对象 cast/receive shadows | 直接占据人体 Gaussian 场景合成与阴影；可作技术 baseline，FastRelight 需扩展到户外大尺度、多类别和动态太阳 |
| 中 | Real2Sim, arXiv:2605.13591 | 4DGS + MPM；实例编辑与碰撞后物理运动 | “physics-aware editable”表述需谨慎；FastRelight 的 physics 应限定为光照传输，不扩张到运动物理 |

## 竞争带来的计划调整

### 不能再使用的主贡献表述

- 首个可编辑、可重打光驾驶场景系统；
- 首个显式前景/背景或静态/动态 Gaussian 分解；
- 首个 feed-forward 驾驶 4DGS；
- 首个支持车辆替换、轨迹修改或天气编辑的 Gaussian simulator；
- 单独把全局环境光、空间光照区域或材质先验作为创新。

### 建议收缩后的三项贡献

1. **方法主贡献：动态跨组件光照传递。** 面向户外太阳/天空和局部灯源，在编辑车辆/行人轨迹后，让所有 Gaussian 组件同时正确 cast 与 receive shadows，且时间连续。
2. **系统贡献：统一 relightable 4D scene-component contract。** rigid、SMPL/LBS、generic deformable 和 static scene 共用 material/light/visibility API；重点是可组合性与误差隔离，不声称组件表示本身新。
3. **证据贡献：CARLA paired-light + edit benchmark。** 同几何不同光照、未见几何/未见光照、对象编辑后的阴影和材质恒定性；同时报告 Waymo 无真值限制。

### 新的必须比较对象

- 全系统：LightSim、DrivingGaussian++、HorizonForge；
- feed-forward reconstruction：DrivingRecon、DynamicVGGT；
- 车辆编辑/relight：MADrive；
- relighting decomposition：GS-ID；
- 动态阴影：Deep Gaussian Shadow Maps；
- 如果代码/输入协议不可公平复现，必须说明并采用 component-level proxy，不能省略。

## 近期 go/no-go 判据

在进入大规模联合训练前，做两个小 probe：

1. `global SH/env + DGSM-style visibility` 是否已经足以击败 QE 提议的 `global + segmented-light MLP`；若是，取消后者作为主创新。
2. 固定 GT geometry/material 时，编辑车辆与行人的 shadow IoU、方向误差和时序 flicker 是否能同时优于 LightSim-style baked/deferred baseline 与 DGSM-style local baseline；若不能，FastRelight 应转为工程系统而非方法论文。

## 稳定标识

已登记：`LIT-537AC4BD205F`、`LIT-C156B17C747C`、`LIT-115789D31C03`、`LIT-F9C476331FA3`、`LIT-6BE73BA19078`、`LIT-59B38FF55E4D`、`LIT-3E7D80D87C6C`、`LIT-B1CE2AA8317B`、`LIT-A91382E33778`、`LIT-89E998CE9AF7`。
