# 2026-08-23 驾驶场景行人重建：SOTA 调研与剩余空间

> 范围：以「驾驶采集条件下的人体/行人重建」为唯一对象，检索其主干谱系、相邻的着衣人体重建、feed-forward 人体重建与人体—场景联合重建。
> 目的：确定真实 SOTA 数字、判断剩余空间、界定可由 3DGS 侧主导的贡献。
> 所有数字来自论文公开正文或项目页；未做任何本地复现。

## 1. 主干谱系

| 时间 | 方法 | 对行人的处理 | LIT |
|---|---|---|---|
| 2024 | Street Gaussians / NSG | 前景仅刚体模型；行人退化为拖影，部分被错误吸收进静态背景 | — |
| 2025 | **OmniRe**（ICLR 2025 Spotlight） | `SMPLNodes`（SMPL + LBS + voxel deformer）与 `DeformableNodes`；配套面向驾驶日志、多相机、强遮挡的人体姿态流水线 | `LIT-*`（已锁 `codebases/manifest.yaml`） |
| 2025-08 | DriveSplat | 非刚体 actor 用全局刚体变换 + 两阶段形变；引入深度与法线先验；NVS 优于 OmniRe | `LIT-E27A56D80AFF` |
| 2026-02 | Nighttime PBR-GS | 行人用 SMPL Gaussians，骑车人与远处行人用 deformable Gaussians；重点在夜间 PBR | `LIT-6CADDC4504A2` |
| 2026 | ReconDrive / DGGT / FRUC / DrivingRecon | feed-forward 4DGS 路线，不对人体作专门建模 | `LIT-295254DA2278` 等 |

## 2. 本调研最关键的发现：human-region 指标的度量空白

OmniRe 在 human region 报告：

| | PSNR | SSIM |
|---|---|---|
| 重建（Reconstruction） | 28.15 | 0.845 |
| 新视角（NVS） | **24.36** | **0.727** |

相对次优基线为 +4.09（重建）/ +3.06（NVS）PSNR。

**该数字至今未被公开超越，原因不是无人做得更好，而是后续方法不报这一项。**

DriveSplat 整体强于 OmniRe，其 Table 1/2 为整场景聚合指标；Table 6 虽专门选取「前视含大量行人」的 Waymo 序列，报告的仍是**全图**指标（OmniRe 37.26 / DriveSplat 37.93 PSNR）。

全图 37.26 与 human-region 28.15 之间约 9 dB 的落差，说明行人像素在全图指标中占比极小、被完全稀释。**这个子问题缺少专门的度量，因此也缺少针对性的方法。** 这是结构性空白。

## 3. 有背书的瓶颈

综述 *Learning-based 3D Reconstruction in Autonomous Driving*（`LIT-334F00637EB0`，v5）就行人重建明确列出两条 open challenge：

- **Degradation at Long Range**：远处行人分辨率低，姿态与相机位姿估计精度受损，重建不稳定。
- **Complex Occlusions**：拥挤交通中行人被反复遮挡，从部分观测恢复完整几何是 "a significant hurdle"。

OmniRe 自身在 §4.2 承认："even state-of-the-art human pose prediction models often struggle to predict accurate poses, especially for pedestrians who are distant or occluded by others."

OmniRe 的 Limitations 另列两条：不显式建模光照导致跨光照元素组合时的 visual harmony 问题；per-scene 优化在相机显著偏离训练轨迹时 NVS 变差。**其 Limitations 未提及衣物。**

## 4. 相邻方向：衣物解耦已被占据

| 工作 | 内容 | LIT |
|---|---|---|
| **CLOTH-HUGS**（2026-04） | body 与 cloth 分为独立 Gaussian 层、共享 canonical space、SMPL 驱动 LBS 与学习 skinning；cloth Gaussians 由 mesh 拓扑初始化，加仿真一致性、ARAP 与 mask 监督；depth-aware 多趟合成；LPIPS 最多降 28% | `LIT-8B84FE3C3F97` |
| ReLoo / MonoCloth / RealityAvatar / GGAvatar / DressRecon / DLCA-Recon | 松散衣物、body/cloth 解耦、可动画化 | `LIT-B36B0F75FBEA` 等 |

共同前提为受控或半受控的单目/多视角人像捕捉：被摄者占据画面主体、分辨率高、观测帧数充足、相机绕人运动。

**结论：把「衣物解耦」作为方法主创新等价于在驾驶数据上重做 CLOTH-HUGS，不成立。**

## 5. 相邻方向：feed-forward 人体与人体—场景联合

- LHM（`LIT-696A8B3ACE37`）、LHM++/PF-LHM、IDOL：单图/少图前馈生成可动画 Gaussian 人体。**未检索到应用于驾驶行人的工作。** 可作为补全观测不足区域的先验模块。
- StudioRecon（`LIT-B320AFDA160F`）：低重叠多视角人体—场景重建，通过跨视角关联与多视角三角化在个别视角被遮挡时仍恢复 SMPL。**设定为室内 studio（体育馆、住宅），非驾驶。**
- Illumination-Consistent Human-Scene Reconstruction（CVPR 2026）、SceneShine（WACV 2026）：人体—场景光照一致联合重建，单目设定。

## 6. 剩余空间的定位

剩余空间不在人体表示上（已被 CLOTH-HUGS 等占据），而在**观测条件**上：

> **在观测严重不足的驾驶采集条件下，如何把人重建出来。**

驱动难点来自采集本身——远距离导致行人在图像中可能仅数十像素高、rig 相机间重叠低、单个行人观测窗口短、相机自身运动、行人间相互遮挡——而非人体表示的表达能力。受控条件下的着衣人体方法全部预设了相反的观测条件。

### 由 3DGS/几何侧主导的三个技术核心

1. **观测充分性建模**：给定 rig 几何、行人轨迹与遮挡关系，判定体表各区域被哪些相机、在哪些时刻、以何种有效分辨率观测；据此分配 Gaussian 容量并决定何时回退到先验。
2. **跨相机 × 跨时刻的观测聚合**：同一行人在多相机多时刻的观测在 canonical space 中的对齐与聚合。
3. **分层 human-region 评测协议**：按距离、遮挡率与可观测帧数分层报告。第 2 节表明该评测在领域内当前缺失，协议本身即构成贡献。

人体先验（SMPL/LBS/garment、LHM 类前馈模型）在此框架中为被调用模块。该分工与领域惯例一致：OmniRe 亦直接使用现成 SMPL 与 4D-Humans。

## 7. 定位的诚实表述

- 本方向**不是新方向**，是 OmniRe 人体分支的改进工作，须按此定位撰写与投稿。
- 剩余空间真实：human-region 的公开 SOTA 停在 24.36 NVS PSNR / 0.727 SSIM 逾一年，后续方法绕开该指标。
- 瓶颈有综述与原作者双重背书。
- 风险：需在 human-region 上取得**大幅度**提升；小数点级改善不足以支撑。
- 致命风险：若分层测量显示 OmniRe 在各层均已足够好，方向不成立。

## 8. 前置判据

在投入方法设计前，必须先完成分层测量，见 `EXP-*`（P0 分层 human-region 基线）。判据：

- 远距/高遮挡分层显著塌陷 → 方向成立，该分层表即论文首图；
- 各层均接近 28 → 立即换题。

## 9. 本次检索的局限

- 共约 14 次检索，覆盖主干谱系、综述、着衣人体、feed-forward 人体与人体—场景联合。
- OmniRe 的 OpenReview 评审意见未取得（被站点验证页拦截），审稿人指出的弱点未纳入。
- 无法保证覆盖 2026 年中之后的全部 preprint。**建议在 Semantic Scholar 上按 human/pedestrian 过滤 OmniRe 的引用列表做一次性核对。**
- CVPR 2026 Illumination-Consistent Human-Scene Reconstruction 仅有 poster 页摘要，无 arXiv 编号，未登记 LIT。
- 所有数字均取自论文，未经本地复现。
