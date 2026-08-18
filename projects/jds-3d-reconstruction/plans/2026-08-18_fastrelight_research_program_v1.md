# FastRelight 研究与实施计划 v1

> 日期：2026-08-18  
> 状态：`P0 — contract-and-reproducible-baseline`  
> 依据：Presentation slides 25–32/41/43/49；QE report Chapter 4 与 §6.2.3  
> 规划方式：阶段门优先；日期是容量估计，不以压缩证据来追赶日历。

## 1. 北极星与可证伪问题

最终演示必须在同一真实驾驶序列中完成：选择一辆车或一个行人，移除/替换/改变轨迹或姿态，切换环境光，再渲染时间连续、遮挡正确、阴影合理、曝光和色调一致的多视角视频。

核心问题：显式组件分解、共享光照与材质/可见性建模，相比外观与光照耦合的 4D 重建，是否在不显著牺牲重建质量与速度的前提下，提高编辑后的光照真实性？

| 假设 | 最小证据 | 证伪/回退 |
|---|---|---|
| H1 组件化 scene graph 能提供可靠对象编辑 | 五类层独立渲染；移除/替换后无明显身份混合和背景污染 | 若分解误差主导，先收缩到背景+刚体车辆，不进入联合重打光 |
| H2 共享环境光 + 空间残差优于独立外观变换 | CARLA held-out light 上超过 global-only 与 per-component baseline | 若残差吸收材质，回退到共享环境光并加强材质恒定约束 |
| H3 时序分解与显式可见性减少光照泄漏 | IDSW、背景时序误差、shadow metric 均有独立改善 | 若 mask/inpaint 仍不可靠，使用合成真值训练并把真实复杂遮挡列为限制 |

对应研究记录：`IDEA-93F257E3E556`、`IDEA-DC38D8C3CC41`、`IDEA-132F2E720420`。

## 2. 范围与非目标

### 2.1 v1 必须交付

1. 五类组件：sky、static background、rigid vehicle、articulated pedestrian、generic deformable。
2. 统一的 canonical/world 坐标、运动、材质、可见性与 light-response 接口。
3. 对象级选择、移除、替换、位姿/轨迹/姿态修改与重新组合。
4. 全局环境光 baseline、空间光照残差、材质表示和 cast-shadow/visibility。
5. CARLA 跨光照真值评估、Waymo 真实数据验证、速度/显存和失败案例。

### 2.2 暂不作为 v1 主线

- radar 融合，除非 LiDAR 合约完成后有明确的恶劣天气或远距收益实验；
- 从零训练几何 foundation model；
- 通用自然语言编辑器、完整资产库、规划/仿真产品集成；
- 完整全局光传输或路径追踪级物理正确性；
- 把单个 sequence 的 per-scene optimization 称为 feed-forward；
- 在真实数据无 relighting GT 时仅凭好看案例宣称物理真实。

## 3. 系统与接口合约

### 3.1 数据合约

```text
SequenceManifest
  sequence_id, dataset, split, timestamps
  cameras: intrinsics, extrinsics, exposure/white-balance metadata
  rgb[time, camera]
  lidar[time] + sensor_to_world
  instances: id, category, masks, track, pose/SMPL when available
  optional: flow, depth, normals, inpainted_background
  lighting: environment_id, parameters, region/shadow labels, GT availability
  edits: target_id, operation, transform/pose/asset/light parameters
```

首版只把 RGB、标定相机和 LiDAR 设为必需输入。所有预测监督必须记录生成模型、版本、阈值和置信度，不能与人工/模拟真值混用。

### 3.2 统一组件合约

```text
SceneComponent
  component_id, category, canonical_frame, world_scale
  canonical_gaussians: mean, rotation, scale, opacity, base appearance
  motion(t): identity | SE(3) | SMPL/LBS | residual deformation
  material_features: explicit fields + confidence
  visibility(camera, t, light): opacity, occlusion, cast/receive-shadow state
  light_response(lighting, view, t) -> appearance
  render(camera, t, lighting)
  edit(operation) -> validated component state
```

约束：对象 ID 在序列内稳定；旋转、尺度、曝光和颜色空间全局统一；组件不能绕过 shared lighting 直接烘焙目标光照；每次编辑必须产生可审计 manifest。

### 3.3 光照最小设计

- `L_global`：跨组件共享的环境光（首个 baseline 可从低阶 SH 或 env map 二选一，经 probe 决定）。
- `L_region(x,t)`：有容量约束的空间残差，表达建筑遮蔽与局部光源；必须防止吸收 albedo。
- `M_component`：车辆/人体/背景的材质特征和类别先验，需跨光照保持稳定。
- `V(x, light, t)`：光照可见性与 cast/receive shadow；不能用单个逐帧 shadow mask 代替完整接口。
- 输出在 linear RGB 中组合，曝光/白平衡作为相机成像项单独处理。

## 4. 数据集与评估协议

### 4.1 数据角色

| 数据 | 角色 | 不可替代的证据 |
|---|---|---|
| CARLA | 可控训练/probe/定量测试 | 同几何、不同太阳/天空/天气的 relight 与 shadow GT |
| Waymo | 真实主验证 | 多视角+LiDAR、真实遮挡和复杂车辆/行人 |
| nuScenes / Argoverse 2 | 可选泛化 | 跨采集系统泛化；不阻塞主线 |
| JDS S3 归档 | 原型恢复 | 人体和背景历史资产，不直接作为独立 benchmark |

数据 split 必须按场景和光照条件隔离。CARLA 至少包含 `seen geometry/unseen light`、`unseen geometry/seen light`、`unseen both` 三个切分；真实数据不得把同一序列的相邻帧随机拆入 train/test。

### 4.2 指标矩阵

| 维度 | 指标/检查 |
|---|---|
| 分解与身份 | mask mIoU、boundary F、IDF1、IDSW、背景污染率、遮挡长度分桶 |
| 几何 | LiDAR depth MAE/AbsRel、normal consistency、轨迹/姿态误差、静态/动态分区 |
| 重建渲染 | PSNR、SSIM、LPIPS；full/static/dynamic/component 分开报告 |
| 时间一致 | tLPIPS、flow-warped photometric error、flicker spectrum/失败视频 |
| 重打光 | CARLA relight PSNR/SSIM/LPIPS、albedo stability、曝光/色温一致性、shadow IoU/边界/方向误差 |
| 编辑 | removal hole/background consistency、插入边界、遮挡次序、接触/投影阴影、轨迹连续性 |
| 效率 | 预处理/训练/推理分开计时，per-scene 与 per-frame latency、FPS、peak VRAM、Gaussian count |
| 真实感 | 预注册的盲法成对偏好；同时公开无 relighting GT 的限制 |

## 5. P0–P6 路线与阶段门

以 1 名主要研究者估算约 24 周；多人可以并行组件恢复，但阶段门依赖不变。

### P0 — 合约与可复现基线（W1–W2）

- 锁定 OmniRe/DriveStudio、LHM 及所有补丁的 URL、commit、license 和环境。
- 建立 `SequenceManifest`、坐标/颜色/曝光回归测试和 8–16 帧 smoke scene。
- 在一个 Waymo 短序列导出 sky/background/vehicle/pedestrian/deformable/composite；无对象的层可为空，但协议必须稳定。
- 将 S3 人体与背景证据映射到代码版本、scene ID、配置、checkpoint 和指标。

**G0：** 同一命令可重跑；manifest 完整；五类输出 schema 通过；至少背景+车辆或背景+行人在短序列可渲染。若失败，禁止开始联合网络。

### P1 — 组件 baseline（W3–W6）

- 恢复背景/天空 feed-forward 或明确区分 per-scene optimized baseline。
- 恢复 canonical rigid vehicle + `SE(3)`；工程化人体 LHM/SMPL/LBS；建立通用形变体最小 baseline。
- 每类独立报告几何、渲染、时序和速度；建立遮挡/实例混合 failure taxonomy。

**G1：** 背景、车辆、行人三条必选线均有锁定 checkpoint 和独立指标；人体至少跨 3 subjects/3 motions；组合指标不低于对应 OmniRe baseline 的预注册容差。generic deformable 可作为后续可裁剪项，但需记录决策。

### P2 — 统一编辑与分解稳健性（W7–W9）

- 实现统一 `SceneComponent`、组件注册表、选择/移除/替换/变换操作。
- 加入实例持续性、遮挡关系和跨帧背景补全约束；比较逐帧 SAM2+inpaint baseline。
- 建立对象移除、车辆换轨迹、行人换姿态三个固定编辑集。

**G2：** 三类编辑可由 manifest 重放；无 ID 冲突/坐标漂移；相对逐帧基线降低 IDSW 与背景时序误差，否则不将复杂遮挡序列送入重打光联合训练。

### P3 — CARLA 光照基准与全局 baseline（W10–W12）

- 生成同几何跨太阳方向、天空、曝光/天气的 paired captures，并保存光照/材质/深度/normal/shadow GT。
- 实现 `L_global` + 相机成像项；先分别测试固定几何与预测几何。
- 对比无分解、per-component appearance transform、global-only 三种 baseline。

**G3：** 数据切分无泄漏；GT 渲染回归通过；global-only 在 held-out light 上形成可复现数值；否则先修基准，不引入空间残差。

### P4 — 材质、空间光照与阴影（W13–W17）

- 建立材质特征/先验与跨光照恒定约束。
- 加入有容量约束的 `L_region`，对 region 数量/表示和 lighting leakage 做消融。
- 加入显式 visibility/cast-shadow，报告 shadow 和跨组件光照一致性。
- 验证 QE 提出的 `L_reg` 是否有效，不预设其成立。

**G4：** 完整模型在三随机种子上优于 global-only；relight、shadow 和 albedo stability 至少两类关键指标有置信区间不跨 0 的改善，且原始重建退化在预注册容差内。失败则去掉空间残差或改为显式可见性优先。

### P5 — 联合训练与编辑后重打光（W18–W21）

- 采用 geometry → decomposition → lighting → limited joint fine-tuning curriculum。
- 完成 removal、replacement、motion/pose、environment-light 四类编辑。
- 做 component representation、inpainting、temporal、material、region lighting、visibility 和 joint-training 消融。

**G5：** 编辑后遮挡与阴影回归通过；CARLA 主表、Waymo 真实序列、效率和失败案例齐全；所有核心贡献可由独立消融支持。

### P6 — 规模验证与证据冻结（W22–W24）

- 扩展场景、三随机种子、长序列与跨数据集测试；冻结 config/checkpoint selection。
- 内部 reviewer 审核 novelty、baseline 公平性、统计、物理主张和失败案例。
- 生成论文表图、匿名配置和最小复现包；投稿 venue 与时间单独确认。

**G6：** 每个论文 claim 能指向锁定 EXP；无“架构图即结果”、无真实数据无真值却声称物理正确、无未披露 per-scene optimization。

## 6. 最小实验矩阵

1. component baselines：background / vehicle / pedestrian / generic deformable 独立及 composite。
2. decomposition：frame mask vs temporal ID vs temporal ID + consistent inpaint/visibility。
3. lighting：baked appearance vs per-component transform vs global-only vs global+region vs full material+visibility。
4. geometry source：GT depth/pose vs LiDAR-supervised prediction，隔离几何误差对 relight 的影响。
5. edits：remove / replace / rigid motion / articulated motion / environment light。
6. seeds：探索实验 1 seed；进入主表的训练方法 3 seeds 并报告置信区间。

## 7. 关键依赖、风险与回退

| 风险 | 早期信号 | 回退 |
|---|---|---|
| 历史代码无法恢复 | 只有视频，无 commit/config/checkpoint | 从官方 OmniRe 锁定 commit 重建 baseline，历史产物仅作参考 |
| 背景补全跨时闪烁 | flow-warp error/LPIPS 高 | 多视角时序补全或只在可观测背景区域训练；不让伪背景污染材质 |
| 遮挡实例混合 | IDSW、边界污染高 | track-level masks、depth ordering、合成遮挡 curriculum |
| 光照残差吸收材质 | albedo 随 light 变化 | 降低残差容量、跨光照材质恒定、显式 visibility |
| 未观测区域使 env light 欠定 | 新视角/背面 relight 崩溃 | sky/env prior、纹理补全置信度；不对不可观测区域作强主张 |
| 联合训练互相破坏 | geometry/render/relight 指标振荡 | 分阶段冻结、stop-gradient、GT→predicted curriculum |
| 范围过宽 | P1 三条必选线不能按门关闭 | v1 裁 generic deformable，其次裁多数据集；不裁复现、CARLA 真值和三种子 |

## 8. 完成定义

“FastRelight 已完成”必须同时满足 G0–G6，并具备：锁定代码 commit、环境、数据 manifest、训练/评估命令、checkpoint、指标 JSON、可追溯编辑 manifest、视频/图像产物和明确限制。仅完成 pipeline design、单组件原型或定性视频都不满足完成定义。

## 9. AI 使用说明

本计划由 AI 辅助读取研究者提供的 PPT/PDF、整理范围和建立证据门。方法有效性、实验数值、代码来源、投稿贡献与物理真实性必须由锁定实验和研究者复核确认。
