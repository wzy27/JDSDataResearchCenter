---
record_id: "LIT-537AC4BD205F"
status: "needs-review"
doi: ""
openalex_id: ""
arxiv_id: "2312.06654"
pmid: ""
---

# LightSim: Neural Lighting Simulation for Urban Scenes

> Intake created from arxiv metadata on 2026-08-18T08:50:20Z. Metadata registration is not evidence verification.

## Bibliographic metadata

- Authors: Ava Pun, Gary Sun, Jingkang Wang, Yun Chen, Ze Yang, Sivabalan Manivasagam, Wei-Chiu Ma, Raquel Urtasun
- Year: 2023
- Venue: arXiv
- Canonical URL: https://arxiv.org/abs/2312.06654

## Screening

- Relevance decision: `direct-competitor-highest-priority`
- Reason: 已覆盖驾驶场景分解、对象编辑与真实感重打光的总体目标。
- Reading priority: P0，必须完整复现/比较。
- Source inspected: `abstract-and-full-text-sections`

## Evidence notes

### Evidence item 1

- Claim: LightSim 已实现动态 actor/静态背景数字孪生、对象插入/修改/移除、太阳与阴影重打光和时序视频。
- Location in source: abstract；supplement limitations/Fig. A26 附近。
- Direction: `contradicts`
- Scope/dataset/population: PandaSet 驾驶场景，另展示 nuScenes 泛化。
- Uncertainty: 需后续完整核对训练/评估协议与代码可用性。

## Methods

- Study design: 物理渲染 + 学习式 deferred renderer，真实/合成 paired-light 训练。
- Data: PandaSet 为主。
- Baselines/comparators: 待全文表格复核。
- Metrics: relighting realism、时序视频与下游感知收益。

## Limitations

- Author-reported: 原始阴影可能烘焙进重建；固定材质；夜间局部光源处理受限。
- Reviewer-observed: 直接否定 FastRelight 总体目标的新颖性，但为动态 4DGS 的统一接口和显式 shadow transport 留出空间。

## Traceability

- Related ideas: `IDEA-DC38D8C3CC41`, `IDEA-132F2E720420`
- Related experiments: `EXP-C4E8F5217892`, `EXP-4C2A9AD4C3D2`
- Related manuscript claims:
- Related figures/tables:

## Verification checklist

- [ ] DOI/identifier resolves to this work
- [ ] Title, authors, year, and venue checked against the source
- [ ] Full-text access and license recorded when relevant
- [ ] Evidence locations recorded from inspected content
- [ ] Limitations captured
- [ ] Project traceability links point to real records
