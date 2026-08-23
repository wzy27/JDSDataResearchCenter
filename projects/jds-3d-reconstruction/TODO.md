# 执行 TODO：双表示互导优化的成立条件

> 任务 ID 由 `project_id + 初始任务文本` 确定；修改描述时保留 ID。完成必须有对应 `EXP-*` 或等价可复现证据。
> 当前方向见 [`sources/2026-08-24_mutual_guidance_position.md`](sources/2026-08-24_mutual_guidance_position.md)（`IDEA-4DC79F20C0C6`）。
> **E-α 与 E-β 未推翻 H1 之前，不进入方法设计。**

## P0 — 前置：可复现性与数据

| 状态 | ID | 优先级 | 行动 | 验收 |
|---|---|---:|---|---|
| [ ] | `TASK-7E31A0C5D9` | P0 | 取得 GS-Octree 代码并复现论文数值 | 在 NeRF-Synthetic 上复现论文报告的至少一个数值，误差在合理范围内 |
| [ ] | `TASK-B24F6E8A11` | P0 | 取得 MGSR 代码（github.com/TsingyuanChou/MGSR）并跑通 | 能在一个场景上完成 2DGS/3DGS 交替优化 |
| [ ] | `TASK-0D9C53BF27` | P0 | 下载 NeRF-Synthetic 与 OmniObject3D，固定评测协议 | 数据 manifest 与 Chamfer/F-score 评测脚本就位并自测通过 |

## P1 — 证伪实验（按此顺序，前者不通过则停）

| 状态 | ID | 优先级 | 行动 | 检验 | EXP |
|---|---|---:|---|---|---|
| [ ] | `TASK-4A8E1FC603` | P0 | 循环消融：A / B / A→B / A↔B 四路对比 | **H1** | `EXP-320CDAC90FCC` |
| [ ] | `TASK-91BD7E2A45` | P0 | 受控误差注入：扰动随迭代收缩还是增长 | **H1 机制** | `EXP-D3E26C0B2BFF` |
| [ ] | `TASK-6C0F82D3E7` | P1 | 旋钮敏感性：细分层级 / warm-up 与切换 / Hessian 退火，对照 3 种子波动 | **H2** | 待建 |
| [ ] | `TASK-E5730BA914` | P2 | 早期可预测性：寻找预示成败的早期可测信号 | **H3**（仅 H1 成立后） | 待建 |

## 待研究者执行

- **通道 B 引文图谱**：在 Semantic Scholar 上查 GS-Octree、MGSR、Neural-Singular-Hessian 的前向引用，确认无人已做该分析。
- **检索盲区**：当前语料仅覆盖 ICCV 2025 与部分 CVPR 2026，**未覆盖 SIGGRAPH / TOG / TVCG** —— 双表示混合与几何正则的工作常发表于图形学场馆，这是最大盲区。
- **组内确认**：LoSF 方向的同学在做拓扑/流形，本方向与之相邻但不重叠，可考虑合作。

## 已完成的方向筛选

- [x] 七个候选方向连续证伪，方法与证据见 [`sources/2026-08-23_survey_methodology.md`](sources/2026-08-23_survey_methodology.md)。
- [x] 建立会议全文正查工具链（`tools/survey.py` 等），语料已缓存 1239 篇。
- [x] 确认收敛性/稳定性分析在语料中主题级为 0，互导与收敛交叉命中为 0。

## 历史范围（驾驶场景，2026-08-23，已终止）

原方向为观测受限条件下的驾驶场景行人重建。终止原因：Hierarchy UGP (ICCV 2025) 已取得 human-region +8 dB；目视核验确认被丢弃的行人绝大多数确属信息不足，明确的模型失败仅 1/53。相关产出（观测充分性分析、分层评测器、`gpu-budget` skill）保留复用。详见 `plans/CHANGELOG.md`。

## 归档：FastRelight 时期的任务 ID（2026-08-18，已终止）

保留于此仅为使历史 `EXP-*` 记录的 task 链接可解析。这些任务不再执行。

| 状态 | ID | 原行动 |
|---|---|---|
| [-] | `TASK-9A7AF40BC2` | 锁定 FastRelight 基线代码、commit、环境和数据清单 |
| [-] | `TASK-DD540CF915` | 统一 RGB、LiDAR、相机、实例、光照和编辑操作的数据合约 |
| [-] | `TASK-C0D73ED316` | 复现一个 Waymo 短序列并导出五类组件层 |
| [-] | `TASK-84E68643E9` | 恢复并验收静态背景与天空基线 |
| [-] | `TASK-E5886BDB18` | 恢复并验收刚性车辆基线 |
| [-] | `TASK-9C662E26DC` | 工程化并扩展行人重建原型 |
| [-] | `TASK-C844EE4497` | 建立通用形变体最小基线 |
| [-] | `TASK-C020D3B4C2` | 建立 CARLA 多光照定量基准 |
| [-] | `TASK-C312DFAB8F` | 实现全局环境光重打光基线 |
| [-] | `TASK-BA65540608` | 实现空间光照残差、材质和阴影可见性 |
| [-] | `TASK-31CE2EFAFC` | 完成联合训练、消融、真实数据验证与论文证据冻结 |

状态标记 `[-]` 表示已归档终止，区别于未开始的 `[ ]`。
