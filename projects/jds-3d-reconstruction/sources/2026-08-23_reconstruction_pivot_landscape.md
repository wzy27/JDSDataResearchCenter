# 2026-08-23 补充调研：转向"重建方向"的可行落点

> 触发条件变更：导师要求成果必须落在**重建**方向；已确认一位专攻人体与衣物重建的合作者；主研究者本人强项为基于 3DGS 的重建。
> 本次检索范围：动态场景 Gaussian 逆渲染、人体—场景联合重建、着衣人体 Gaussian 重建、驾驶场景行人建模、CARLA 跨光照数据。
> 本文只记录检索到的公开信息与由此产生的判断，方法有效性仍需锁定实验验证。

## 1. 本次新增的直接冲突（在 2026-08-18 竞争格局之外）

| 强度 | 工作 | 已占据的能力 | 对现有计划的影响 | LIT |
|---|---|---|---|---|
| 极高 | Illumination-Consistent Human-Scene Reconstruction from Monocular Video, CVPR 2026 | 3DGS 人体—场景光度一致联合重建；**learnable light volume 向 human Gaussians 提供局部光照线索**；空间变化光照与阴影 | 直接占据 `IDEA-DC38D8C3CC41` 的"共享环境光 + 空间光照残差作用于组件"核心表述。该 idea 不能再作为主创新 | 未登记（暂无 arXiv 号） |
| 极高 | LumiMotion, arXiv:2604.10994 | 首个利用**场景动态作为逆渲染监督**的 Gaussian 方法；motion 使同一表面在不同光照下被观测，用于解耦材质与光照；albedo LPIPS +23%、relighting +15% | 占据"用运动/时序变化监督材质—光照分解"这一表述。任何以此为卖点的主张都需改为借用而非首创 | `LIT-8EC7C5EB565B` |
| 高 | Nighttime Autonomous Driving Scene Reconstruction with Physically-Based Gaussian Splatting, arXiv:2602.13549 | 驾驶复合 Gaussian 表示中集成 PBR；联合优化 BRDF 材质、global illumination 漫反射与 anisotropic SG 高光；nuScenes + Waymo 验证并保持实时 | 占据"驾驶场景 Gaussian 的材质—光照物理分解"。FastRelight 的 P4 材质线不再具备首创性 | `LIT-6CADDC4504A2` |
| 中高 | ReLumix, arXiv:2509.23769 | 发布 **CARLA Relight**：record-and-replay 保证几何/位姿/视角完全一致，仅光照为变量；9 个 town、75 场景、15 种天气光照、每对 1500 帧 | 削弱"自建 CARLA paired-light 基准"作为证据贡献；但可直接复用，省掉 `TASK-C020D3B4C2` 的数据生成周期 | `LIT-3F979628DBA4` |

## 2. 与本次转向相关的邻域现状

### 2.1 着衣人体 Gaussian 重建（合作者方向）

ReLoo (`LIT-B36B0F75FBEA`)、MonoCloth (`LIT-0FEBA0C3BF45`)、RealityAvatar (`LIT-0215EC756CB8`)、GGAvatar、DressRecon、DLCA-Recon 等已形成密集竞争，覆盖 garment 分离、松散衣物动力学、body/cloth 解耦与可动画化。

共同前提：**受控或半受控的单目/多视角人像视频**——被摄者占据画面主体、分辨率高、观测帧数充足、相机基本围绕人物、光照相对稳定。

### 2.2 驾驶场景中的人体建模

- OmniRe `SMPLNodes`：模板化 SMPL + LBS，外观与光照耦合，无衣物层。官方与第三方均记录其失败模式：行人退化为拖影/鬼影，甚至被错误吸收进静态背景，而这些正是评估驾驶策略最关键的对象。
- Waymo-3DSkelMo (`LIT-DA08AE46A3C9`)：从 Waymo 导出时序一致的 3D 骨架运动，含交互语义。属于**姿态/运动**资产，不涉及外观与衣物重建。
- LiDAR-HMR 等：以 SMPL 先验从稀疏 LiDAR 恢复网格，同样不涉及外观。

### 2.3 判定

着衣人体重建圈全部在受控捕捉条件下；驾驶场景人体圈全部停留在骨架/位姿或外观耦合的 SMPL Gaussian。**两个圈子的交集当前为空。**

## 3. 由此得到的可行落点

> **驾驶采集条件下的着衣行人重建。** 从行车日志（多相机、远距离、低分辨率、强遮挡、单个行人观测窗口短、相机自身运动）重建 garment/body 解耦的行人 Gaussian；将行人穿行于户外空间变化光照（日照与建筑阴影）所产生的外观变化，用作**重建监督**以抑制把阴影烘焙进外观，而不是把重打光作为卖点。

这是一个重建问题，符合导师约束；难点来自采集条件而非渲染方程，因而不与第 1 节的光照类工作正面冲突。

### 可证伪的核心问题

显式 garment/body 分解与跨帧光照归一化，能否在驾驶采集条件下把行人重建质量提升到同时超过：(a) OmniRe `SMPLNodes` 基线；(b) 将受控条件着衣方法直接移植到驾驶 crop 的基线？

### 与现有资产的对应

已有的 Patch10 StageA 数字全部是**重建质量**指标而非重打光指标，方向一致：

| 指标 | base | 已达成 |
|---|---|---|
| dynamic PSNR | 20.2916 | 24.1217 |
| dynamic LPIPS | 0.0838 | 0.0769 |
| cloth alpha IoU（窗口均值） | 0.8228 | 0.8832 |
| outside-occ-aware 泄漏 | 0.005512 | 0.001937 |

Forwardrobe 基线中被关闭的 clothing segmentation、garment/body split 与 albedo×shading decomposition，在本落点下从"未启用的附加项"变为方法主体。

### 建议的评测协议

- 主指标：行人 crop 的 novel-view PSNR/SSIM/LPIPS、mask IoU、时序 flicker。
- 关键差异化：**按距离、遮挡率、可观测帧数分层报告**。受控条件方法无法给出这条曲线，这是驾驶设定独有的证据。
- 可控消融：复用 ReLumix 的 CARLA Relight，取几何/视角一致、仅光照变化的配对，量化"阴影是否被烘焙进 albedo"。不自建数据集。

### 需要立即执行的低成本判据

在单个 Waymo 序列上测量 OmniRe `SMPLNodes` 的行人重建质量相对**距离 / 遮挡率 / 观测帧数**的退化曲线。

- 若退化陡峭 → 存在可观 headroom，方向成立；
- 若 OmniRe 在多数行人上已足够好 → 立即换题，代价仅为一次基线评测。

该判据只需基线推理与评测，不需要新方法实现。

## 4. 对现有台账的影响

- `IDEA-DC38D8C3CC41`（共享环境光 + 空间光照残差）：核心表述被 CVPR 2026 人体—场景工作占据，应降级或标记 challenged，不再作为主创新。
- `TASK-C020D3B4C2`（自建 CARLA 多光照基准）：建议改为复用 CARLA Relight，仅补充所需的 material/normal/shadow 通道。
- P1 的车辆与背景恢复线（`TASK-E5886BDB18`、`TASK-84E68643E9`）：在本落点下不再是必选主线，应降级为集成所需的最小可用件。
- 竞争格局文档中提出的"动态跨组件 shadow transport"主贡献：属于渲染/重打光贡献，与导师的重建约束不符，建议不作为主线。

## 5. 本次检索的局限

- CVPR 2026 那篇仅取得标题、作者与 poster 页摘要，未获全文，其是否处理衣物、是否涉及户外大尺度尚未确认，需补全文核对。
- SceneShine (WACV 2026) 的 PDF 取回被拒（HTTP 403），仅有二手摘要，需人工下载核对。
- 上述判断均基于摘要与项目页，尚无任何本地复现证据。
