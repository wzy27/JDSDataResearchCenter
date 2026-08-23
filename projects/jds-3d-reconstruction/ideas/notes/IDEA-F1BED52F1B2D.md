---
idea_id: "IDEA-F1BED52F1B2D"
status: "proposed"
kind: "hypothesis"
---

# 驾驶采集条件下的着衣行人重建

> 本页记录研究想法及其演变；机器可读状态以对应 JSON 记录为准。

## 当前表述

在驾驶日志的远距离、低分辨率、强遮挡与短观测窗条件下，显式 garment/body 分解配合跨帧光照归一化，能把行人重建质量提升到同时超过 OmniRe SMPLNodes 基线与受控条件着衣方法的直接移植。

## 动机

着衣人体重建全部在受控单目/多视角捕捉下发展；驾驶场景人体建模停留在骨架/位姿或外观耦合的 SMPL Gaussian。两个方向的交集当前为空，且团队同时具备两侧能力。

## 来源与归属

- `sources/2026-08-23_reconstruction_pivot_landscape.md`

初始记录由 Agent 根据已注明来源整理，需由研究者继续评审。

## 假设与前提

- 驾驶采集条件下行人重建质量随距离、遮挡率和可观测帧数存在显著退化，OmniRe SMPLNodes 留有可观 headroom
- 行人穿行于日照与建筑阴影所产生的外观变化可作为重建监督，抑制阴影被烘焙进外观

## 已考虑的替代方案

- 沿用外观耦合 SMPLNodes 并仅增加分辨率/密度
- 把受控条件着衣方法直接移植到驾驶行人 crop

## 验证与证伪

### 成功标准

- 行人 crop 的 novel-view PSNR/SSIM/LPIPS 与 mask IoU 同时优于两类 baseline，且按距离/遮挡率/观测帧数分层后改善在各层一致

### 失败信号

- OmniRe SMPLNodes 在多数行人上退化曲线平缓，headroom 不足以支撑方法贡献

### 计划实验

- 尚未关联 `EXP-*`。

## 演变记录

- 2026-08-23T05:19:55Z `captured`：首次登记。

## 可追溯关系

- 相关文献：LIT-DA08AE46A3C9, LIT-B36B0F75FBEA, LIT-0FEBA0C3BF45, LIT-0215EC756CB8
- 相关 TODO：尚未关联
- 相关实验：尚未关联
- 相关论文结论：尚未关联
