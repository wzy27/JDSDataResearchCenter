---
experiment_id: "EXP-4C2A9AD4C3D2"
status: "blocked"
type: "ablation"
---

# P4 全局/空间光照、材质与可见性消融

> 这是实验计划与证据索引，不代表实验已经执行。

## 目标

检验空间光照残差、材质先验和显式阴影可见性是否各自改善跨光照与编辑后真实性。

## 当前状态

- 状态：`blocked`
- 执行器：`未配置`
- 加速器：`unknown` × 1
- 类型：`ablation`

## 阻塞项

- `UPSTREAM_GATES`：依赖 P1–P3 阶段门通过；解除条件：组件、编辑和 CARLA baseline 实验完成并关联
- `METHOD_UNPINNED`：材质、区域光照和 visibility 参数化尚未由 probe 锁定；解除条件：用小规模 probe 锁定表示、容量和损失

## 协议

三随机种子；固定数据切分和 checkpoint selection；同时报告重建退化。

### 成功标准

- 完整模型优于 global-only
- 关键改善的置信区间不跨 0
- albedo stability 和 shadow 指标不因视觉指标提升而恶化

### 失败标准

- 空间残差吸收材质
- 阴影与遮挡关系错误
- 只有定性案例无统计证据

## 代码、数据与环境

- 代码仓：待确认
- Commit：`待确认`
- 数据：0 个已登记数据入口
- OS：`待确认`
- 命令：`[]`

## 可追溯关系

- Idea：IDEA-DC38D8C3CC41, IDEA-132F2E720420
- TODO：TASK-BA65540608, TASK-31CE2EFAFC
- 文献：尚未关联
- Claim：尚未关联

## Preflight

- 最新状态：`not-run`
- 报告：尚未生成或请查看机器记录中的 report 指针。

## 结果与解释

尚未执行，不得据此更新 Idea 或论文结论。
