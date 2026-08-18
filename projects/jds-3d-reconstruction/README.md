# FastRelight：可编辑、可重打光的 4D 驾驶场景重建

## 研究目标

以 OmniRe 的显式动态场景分解为起点，从同步多视角 RGB 与 LiDAR 重建五类可独立控制的 Gaussian 组件：天空、静态背景、刚性车辆、骨骼驱动行人和通用形变体。系统应支持对象移除、替换、位姿/轨迹修改和环境光改变，并让重组结果在几何、遮挡、阴影、曝光和色调上保持一致。

FastRelight 的研究问题不是“把几个重建模块接起来”，而是：

> 显式组件分解、共享光照表示与材质/可见性建模，能否在保持重建质量和速度的同时，使驾驶场景编辑后的光照比外观耦合的 4D 重建更真实、更稳定？

## 当前结论

两份研究材料均把 FastRelight 定义为在研系统。QE report 第 6.2.3 节明确说明：**总体管线设计已经建立，完整实现与规模化验证仍是未来工作**。当前可复用资产主要是人体重建原型；车辆、背景、统一编辑和物理可信重打光均未形成可复现实验闭环。

| 工作线 | 当前成熟度 | 下一验收门 |
|---|---|---|
| 总体架构 | 设计完成 | 锁定接口、代码/数据版本和最小端到端序列 |
| 行人 | 原型 | 去硬编码、补旋转/LBS、跨人物与动作验证 |
| 车辆 | 未恢复 | OmniRe rigid actor 可复现且有独立指标 |
| 背景/天空 | 只有产物线索 | 配置、checkpoint、几何和时序指标齐全 |
| 通用形变体 | 设计项 | 建立最小可运行基线 |
| 重打光 | 概念/数据准备 | CARLA 真值基准与全局光照 baseline |
| 统一编辑 | 人体替换原型 | 五类组件统一接口和编辑回归测试 |

详细证据见 [`progress.md`](progress.md)。

## 已锁定的 v1 范围

- 输入：同步多视角 RGB、相机标定/位姿与 LiDAR；实例掩码、轨迹、光流和背景补全可作为监督。
- 输出：组件化 4D Gaussian scene graph、材质特征、全局环境光与空间光照残差。
- 编辑：对象选择、移除、替换、刚体变换、行人姿态/轨迹修改、环境光修改。
- 定量主战场：CARLA 的跨光照真值；Waymo 为真实数据主集，nuScenes/Argoverse 2 为规模允许时的泛化集。
- v1 不承诺：雷达融合、任意天气生成、完整物理路径追踪、通用资产编辑器或实时产品化。

## 项目入口

- [`plans/2026-08-18_fastrelight_research_program_v1.md`](plans/2026-08-18_fastrelight_research_program_v1.md)：范围、接口、阶段门、实验与风险。
- [`TODO.md`](TODO.md)：带稳定 TASK ID 的执行视图。
- [`sources/2026-08-18_fastrelight_qe_and_presentation_intake.md`](sources/2026-08-18_fastrelight_qe_and_presentation_intake.md)：PPT/QE report 的 FastRelight 证据摘录。
- [`progress.md`](progress.md)：已有资产与实际完成度审计。
- [`sources/2026-08-18_drivestudio_p0_baseline_audit.md`](sources/2026-08-18_drivestudio_p0_baseline_audit.md)：锁定的上游 commit、组件映射和执行阻塞。
- [`sources/2026-08-18_fastrelight_competitive_landscape.md`](sources/2026-08-18_fastrelight_competitive_landscape.md)：直接竞品、被占据的贡献与收缩建议。
- [`ideas/index.json`](ideas/index.json)、[`experiments/index.json`](experiments/index.json)：研究假设和实验台账。

## 仓库边界

原始文档、S3 数据、视频、数据集、模型权重和训练输出不进入 Git。完成项必须能追溯到代码 commit、数据 manifest、命令、环境、指标和产物；只有架构图、文件名或渲染视频不能标记为“已完成”。
