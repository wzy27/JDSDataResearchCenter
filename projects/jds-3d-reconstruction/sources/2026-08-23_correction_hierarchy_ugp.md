# 2026-08-23 更正：漏检 Hierarchy UGP 与 UGSDF，及其对论点的影响

> 本文更正先前多份文档中的一处事实错误，并记录漏检的原因与由此确立的调研方法。

## 1. 更正的事实

先前 [`2026-08-23_pedestrian_reconstruction_sota_survey.md`](2026-08-23_pedestrian_reconstruction_sota_survey.md) 与项目 README 中的表述：

> 「human-region 的公开 SOTA 至今仍是 OmniRe 的 28.15 / 24.36，因为后续方法不报这一项。」

**该表述不成立。** Hierarchy UGP（ICCV 2025，浙江大学 + 理想汽车）在 Waymo 上明确报告了行人区域指标。

### Hierarchy UGP, Table 2（Waymo，`*` 列为 pedestrian regions）

| | 场景 014 PSNR* | 场景 023 PSNR* |
|---|---:|---:|
| **Scene Reconstruction** | | |
| Street GS | 23.33 | 24.75 |
| OmniRe | 22.16 | 29.23 |
| Hierarchy UGP | **30.20** | **34.10** |
| 相对 OmniRe | +8.04 | +4.87 |
| **Novel View Synthesis** | | |
| OmniRe | 19.61 | 23.07 |
| Hierarchy UGP | **24.23** | 21.64 |
| 相对 OmniRe | +4.62 | **−1.43** |

该文并明确批评 OmniRe 的 SMPL 依赖，原文：

> "OmniRe models pedestrians using the SMPL model, specifically designed for human modeling, and applies deformable-GS to parts that SMPL cannot fit. While this approach achieves good results by controlling these parts using spatial information, **it is limited in its general applicability, and the reconstruction quality of parts that SMPL cannot fit remains suboptimal.**"

其方法以统一的 Unified Gaussian Primitive 表示刚性与非刚性动态，**不使用 SMPL 模板**——即本项目所识别的「姿态门」在该方法中已不存在。

同期的 UGSDF（`Leveraging 2D Priors and SDF Guidance for Dynamic Urban Scene Rendering`，ICCV 2025，`LIT-386FBB6C449E`）方向一致：不要 3D box、不要 tracklet、不要 SMPL 模板，纯 2D 先验加 SDF，行人同样按通用形变体处理。

## 2. 被削弱的论点

| 原论点 | 现状 |
|---|---|
| human-region 存在度量空白 | **部分不成立**。Hierarchy UGP 已报告行人区域指标 |
| OmniRe 人体分支的 headroom 无人利用 | **已被利用**，重建 +8.04 dB。原定「最差格与最好格差 ≥ 2 dB」的 headroom 判据因此失去意义 |
| 移除 SMPL 二值门可作为方法创新 | **已被做掉** |

## 3. 仍然成立的部分

1. **无人做诊断。** Hierarchy UGP 指出 OmniRe「受限于 SMPL」，但未量化**为什么失败、失败了多少、边界在哪**。本项目已有：105/105 漏检发生在检测/关联阶段、43 倍的二值化容量差、覆盖率随分辨率非单调、993 px 完全无遮挡行人仍被漏。这些该文一条未涉及。
2. **其 NVS 结果不稳定**：一个场景 +4.62 dB，另一个 **−1.43 dB**。拆掉姿态门并未解决观测受限问题。
3. **只有 2 个 Waymo 场景，无任何分层分析**。按距离、遮挡率、有效像素分辨率的退化曲线仍无人给出。
4. **代码未发布**。仓库 `LiAutoAD/HierarchyUGP` 仅含 README 与 images，最后一次 push 为 2024-12-20；论文称 "We plan to release" 但至今未发。因此无法作为可运行 baseline，比较须采用 component-level proxy 并如实说明。

## 4. 论点的重新表述

> **拆掉姿态门不等于解决观测受限。** 无人按观测充分性分配容量，也无人量化可重建边界。

关键转机：OmniRe 中 105 个无姿态行人所走的 `DeformableNodes` 路径，本身即「无模板统一表示」。**若这些实例在分层评测上依然崩溃，即直接证明拆掉姿态门不足，还须按观测充分性分配容量。** 该证据由 E1 产出，不依赖 Hierarchy UGP 的代码。

## 5. 漏检原因分析

Hierarchy UGP 的标题为 *Hierarchy Unified Gaussian Primitive for Large-Scale Dynamic Scene Reconstruction*，**不含 pedestrian、human、SMPL 中任何一词**；其行人区域指标位于 Table 2，摘要中亦未提及。

先前调研的四项缺陷：

| 缺陷 | 表现 |
|---|---|
| 只按主题关键词检索 | 方法可以解决行人问题却不使用行人词汇（「unified primitive」而非「pedestrian」） |
| 只看标题与摘要 | 关键证据在正文表格中 |
| 过度偏重 arXiv 与 2026 | 忽略 2025 年的会议论文集 |
| 未做会议全量枚举 | 未系统遍历 ICCV/CVPR 已录用论文 |

## 6. 由此确立的调研方法

见 [`2026-08-23_survey_methodology.md`](2026-08-23_survey_methodology.md)。核心为两阶段全文正查：会议全量枚举 → 宽松标题粗筛 → 下载 PDF 抽全文 → 精确探针词计分。工具为 [`../tools/survey.py`](../tools/survey.py)。

**该工具的验收标准是能够命中 Hierarchy UGP。** 未通过此验收前，其结论不得采信。
