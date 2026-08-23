# 2026-08-23 OmniRe 引用链复核（JDSDataResearchCenter 现状更新）

回答先行：这个目录里**还没有做过你指定的 OmniRe（arXiv:2408.16760）引文级检索复核**。  
已有内容（`sources/2026-08-23_pedestrian_reconstruction_sota_survey.md`）是基于内部文献池的 SOTA 盘点，已提到“未覆盖 2026 年中之后全部 preprint，建议按 human/pedestrian 重检”，但并没有落到 Semantic Scholar 引文级列表的执行记录里。

我按你要求的策略（OmniRe → Citations → 关键词 human/pedestrian/SMPL）补了一个人工复核补充，核心结论如下：

1. 已命中并对应已入库条目的：
   - OmniRe baseline / DriveSplat / Nighttime PBR-GS / ReconDrive / DrivingRecon / FRUC / DrivingGaussian++ 等（见已存在 `LIT-*`）
   - CLOTH-HUGS、LHM、StudioRecon、Illumination-Consistent Human-Scene Reconstruction、SceneShine 等人体相关方法，已记录为“方法主线”而非 OmniRe 引文链主项

2. 未在现有 `literature/records` 中看到的候选（按关键词检索后更可能是 OmniRe 2026 引文链中的潜在线索）：
   - `XSIM / 2602.05617`（强调统一车辆与行人传感模拟，继承 OmniRe 风格节点，但更偏传感重建框架）
   - `From Concept to Capability, 2605.01995`（偏评估与可控驾驶场景重建，未必直接为人体分支做建模）
   - `Visually-grounded Humanoid Agents, 2604.08509`（更偏 humanoid agent 与人体交互，未专门落点到 OmniRe）
   - `CHROMM, 2603.12789`（与多视角人体重建相关，非专门针对驾驶场景）
   - 以及 ICCV 2025 的 `Hierarchy UGP`、`Leveraging 2D Priors and SDF Guidance for UGSDF`（并非 2026，但对 OmniRe 人体分支空间有直接重叠/压力）

3. 对你最关心的问题（改进驾驶场景人体建模 / 远距离/遮挡行人）给建议：
   - 距离与遮挡主要问题**不在当前仓库结论里被证伪**，反而是当前最有价值空白；
   - 目前仓库已有的高信号结论仍成立：**目前没有看到“直接证明在 OmniRe 直接 human branch 指标上显著超越（尤其 human-region, long-range, occlusion）的已发布工作在同一评测口径下落地**；
   - 但仓库尚缺“citation-filter 扫描日志”，建议按你原始规则补一次可追踪条目（文件化为 `s2_omnire_citation_followup.json`），优先补齐以下三类：
     1. 以 `SMPLNodes`、`human-region`、`long-range / far distance`、`occluded` 为题眼的行文；
     2. 以驾驶场景为数据域（Waymo / nuScenes / PandaSet / KITTI-360）并显式给到 human-region 子指标；
     3. 对比对象明确包含 OmniRe（直接引用或同组基线）且有可复现实验的工作。

更新建议（落地版）：
1. 先在 `sources/2026-08-23_pedestrian_reconstruction_sota_survey.md` 后追加“Semantic Scholar 引文复检更新”节，记录本次复核结果与缺口；
2. 在 `literature/index.json` 之外新增一个 `sources/` 条目，写明本次检索规则、时间戳和未入库条目清单；
3. 把 `EXP` 的 go/no-go 标准加一条：若该复核发现存在可比照 human-region 的直接对比工作，则优先改为“方案对齐/竞品对抗”，否则按“评测优先”路线推进现有分层指标。

如果你要，我下一步可以直接把上述建议做成三项 commit 级变更：  
（1）给现有 survey 文件加“复核结果段”；  
（2）新建 citation 补录日志文件；  
（3）给 `README.md` 和 `plans/CHANGELOG.md` 加一句可追踪的里程碑备注。
