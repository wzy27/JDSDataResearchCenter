# FastRelight 执行 TODO

> 任务 ID 由 `project_id + 初始任务文本` 确定；修改描述时保留 ID。完成必须有对应 `EXP-*` 或等价可复现证据。

## P0 — 当前：合约与可复现基线

| 状态 | ID | 优先级 | 行动 | 验收 | Idea | 依赖 | 来源 |
|---|---|---:|---|---|---|---|---|
| [ ] | `TASK-9A7AF40BC2` | P0 | 锁定 FastRelight 基线代码、commit、环境和数据清单 | OmniRe/DriveStudio、LHM、补丁、license、环境和 checkpoint 均有 hash/版本 | `IDEA-93F257E3E556` | — | QE §6.2.3；S3 audit |
| [ ] | `TASK-DD540CF915` | P0 | 统一 RGB、LiDAR、相机、实例、光照和编辑操作的数据合约 | 8–16 帧 manifest 通过 schema、坐标、颜色空间和曝光回归测试 | `IDEA-93F257E3E556` | `TASK-9A7AF40BC2` | QE pp.46–51 |
| [ ] | `TASK-C0D73ED316` | P0 | 复现一个 Waymo 短序列并导出五类组件层 | sky/background/vehicle/pedestrian/deformable/composite schema 齐全，可为空层但不可缺协议 | `IDEA-93F257E3E556` | `TASK-DD540CF915` | PPT 27–29 |

## P1 — 组件独立验收

| 状态 | ID | 优先级 | 行动 | 验收 | Idea | 依赖 | 来源 |
|---|---|---:|---|---|---|---|---|
| [ ] | `TASK-84E68643E9` | P0 | 恢复并验收静态背景与天空基线 | 锁定 checkpoint；novel-view、LiDAR depth、时序和速度指标齐全 | `IDEA-93F257E3E556` | `TASK-C0D73ED316` | QE pp.48–49 |
| [ ] | `TASK-E5886BDB18` | P0 | 恢复并验收刚性车辆基线 | canonical vehicle + SE(3) 可复现；独立几何/轨迹/渲染指标齐全 | `IDEA-93F257E3E556` | `TASK-C0D73ED316` | QE p.48 |
| [ ] | `TASK-9C662E26DC` | P0 | 工程化并扩展行人重建原型 | 无路径/ID 硬编码，rotation/LBS 完成，至少 3 subjects × 3 motions | `IDEA-93F257E3E556` | `TASK-C0D73ED316` | QE p.48；S3 audit |
| [ ] | `TASK-C844EE4497` | P1 | 建立通用形变体最小基线 | 至少一个非 rigid/SMPL 对象可独立训练、渲染和评估 | `IDEA-93F257E3E556` | `TASK-C0D73ED316` | QE p.49 |

## P2–P4 — 编辑与重打光

| 状态 | ID | 优先级 | 行动 | 验收 | Idea | 依赖 | 来源 |
|---|---|---:|---|---|---|---|---|
| [ ] | `TASK-56ED48CC9E` | P0 | 实现统一组件接口与对象级编辑操作 | removal/replacement/rigid motion/articulated motion 均可由 manifest 重放 | `IDEA-93F257E3E556`, `IDEA-132F2E720420` | P1 三条必选组件 | QE pp.46–50 |
| [ ] | `TASK-C020D3B4C2` | P0 | 建立 CARLA 多光照定量基准 | paired GT、无泄漏 split、材质/depth/normal/shadow/light metadata 完整 | `IDEA-DC38D8C3CC41` | `TASK-DD540CF915` | QE pp.52–53 |
| [ ] | `TASK-C312DFAB8F` | P0 | 实现全局环境光重打光基线 | fixed/predicted geometry 都有 held-out-light 数值，并与 baked/per-component 比较 | `IDEA-DC38D8C3CC41` | `TASK-C020D3B4C2` | QE p.50 |
| [ ] | `TASK-BA65540608` | P0 | 实现空间光照残差、材质和阴影可见性 | 三种子优于 global-only；relight/shadow/albedo stability 有独立消融 | `IDEA-DC38D8C3CC41`, `IDEA-132F2E720420` | `TASK-C312DFAB8F`, `TASK-56ED48CC9E` | QE pp.50–51；PPT 49 |

## P5–P6 — 联合验证与证据冻结

| 状态 | ID | 优先级 | 行动 | 验收 | Idea | 依赖 | 来源 |
|---|---|---:|---|---|---|---|---|
| [ ] | `TASK-31CE2EFAFC` | P0 | 完成联合训练、消融、真实数据验证与论文证据冻结 | CARLA/Waymo 主表、编辑集、效率、三种子、失败案例和锁定复现包齐全 | 全部 | G0–G5 | QE pp.52–55, §6.2.3 |

## 已完成的项目治理

- [x] 两份 FastRelight 材料已按页/slide 摘录并记录 SHA-256。
- [x] v1 范围、非目标、组件/数据合约、评估矩阵和 G0–G6 阶段门已建立。
- [x] S3 三个对象已只读盘点；大文件和个人资料保持在 Git 外。
