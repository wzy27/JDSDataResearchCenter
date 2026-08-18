---
record_id: "LIT-B1CE2AA8317B"
status: "needs-review"
doi: ""
openalex_id: ""
arxiv_id: "2601.01660"
pmid: ""
---

# Animated 3DGS Avatars in Diverse Scenes with Consistent Lighting and Shadows

> Intake created from arxiv metadata on 2026-08-18T08:50:20Z. Metadata registration is not evidence verification.

## Bibliographic metadata

- Authors: Aymen Mir, Riza Alp Guler, Jian Wang, Gerard Pons-Moll, Bing Zhou
- Year: 2026
- Venue: arXiv
- Canonical URL: https://arxiv.org/abs/2601.01660

## Screening

- Relevance decision: `direct-competitor-shadow-method`
- Reason: 直接解决动态 Gaussian avatar/对象在 Gaussian 场景中的光照与 cast/receive shadow。
- Reading priority: P0，方法 baseline。
- Source inspected: `full-text`

## Evidence notes

### Evidence item 1

- Claim: Deep Gaussian Shadow Maps 使用闭式 Gaussian transmittance 与 octahedral atlas，结合 SH HDRI probe 实现快速动态阴影和重打光。
- Location in source:
- Direction: `contradicts`
- Scope/dataset/population:
- Uncertainty:

## Methods

- Study design:
- Data:
- Baselines/comparators:
- Metrics:

## Limitations

- Author-reported: 假设光源附近场景静态，并依赖光源估计质量。
- Reviewer-observed: FastRelight 需证明户外大尺度、多类别、动态太阳和时序编辑下的额外价值。

## Traceability

- Related ideas: `IDEA-DC38D8C3CC41`, `IDEA-132F2E720420`
- Related experiments: `EXP-4C2A9AD4C3D2`
- Related manuscript claims:
- Related figures/tables:

## Verification checklist

- [ ] DOI/identifier resolves to this work
- [ ] Title, authors, year, and venue checked against the source
- [ ] Full-text access and license recorded when relevant
- [ ] Evidence locations recorded from inspected content
- [ ] Limitations captured
- [ ] Project traceability links point to real records
