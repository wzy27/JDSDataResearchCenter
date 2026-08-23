# 执行 TODO：观测受限条件下的驾驶场景行人重建

> 任务 ID 由 `project_id + 初始任务文本` 确定；修改描述时保留 ID。完成必须有对应 `EXP-*` 或等价可复现证据。
> 当前唯一主线是 P0 分层基线测量（`EXP-D364146FE7A6`）。在其结论产出前不进入方法设计。

## P0 — 分层 human-region 基线（go/no-go 前置判据）

| 状态 | ID | 优先级 | 行动 | 验收 | 依赖 |
|---|---|---:|---|---|---|
| [x] | `TASK-3B7E2A91C4` | P0 | 登记 Linux+NVIDIA executor 并构建上游可运行环境 | `wsl2-ubuntu2404-rtx4090` 已登记；DriveStudio `e59bda4f` + 四个 CUDA 扩展全部导入通过，gsplat kernel 在 sm_89 实跑 | — |
| [x] | `TASK-5F1C88D0E2` | P0 | 获取并预处理小规模数据集 | nuScenes v1.0-mini 已下载（SHA-256 已记录）、10 场景 CPU 预处理完成、官方预处理人体姿态已就位 | `TASK-3B7E2A91C4` |
| [x] | `TASK-A46D19FB73` | P0 | 审计行人观测条件分布并检验分层轴 | 227 个行人实例统计完成；有效像素分辨率轴成立，观测次数轴证伪，遮挡轴代理不可用 | `TASK-5F1C88D0E2` |
| [x] | `TASK-C7E0B25A48` | P0 | 获取 SMPL v1.1 neutral 模型 | 已就位并验证：`SMPLLayer` 加载成功，6890 顶点 / 13776 面，sha256 `4924f235…5688`。权重不入 Git | — |
| [~] | `TASK-91DA4E6C0F` | P0 | 生成 sky mask 与 fine dynamic mask | 上游 mmcv/cu111 环境不支持 sm_89，已改用同权重 HF SegFormer；场景 000/001/008 生成中，节流实测 duty 0.596 | `TASK-5F1C88D0E2` |
| [x] | `TASK-6E8B03FA27` | P0 | 用像素级方法重新定义遮挡分层轴 | 凸包光栅化 + 深度排序；面积加权可见比 p50=0.701，31.3% 的行人 <0.5，具区分度。与像素高度轴 Spearman 0.199，近似独立 | `TASK-A46D19FB73` |
| [x] | `TASK-DB25F7194C` | P0 | 实现分层 human-region 评测脚本 | 二维分层 12 格每格 ≥10 实例；自测通过：噪声单调性、分层分辨力（目标层 −12.15 dB / 其余 −0.02 dB）。与真实渲染输出的帧号对接未核对 | `TASK-6E8B03FA27` |
| [ ] | `TASK-04AC6E3D85` | P0 | 复现 OmniRe 基线并产出分层退化曲线 | 至少 3 个行人密集场景（000/001/008）完成训练与评测；整体 human-region 数值与论文量级可比。训练须经 `gpu-budget` 约束并报告实测占空比 | `TASK-91DA4E6C0F` |

**G0 判据：** 远距/低分辨率分层显著塌陷 → 方向成立，进入方法设计；各层均接近整体水平 → 立即换题。

## P1 — 方法设计（G0 通过后才启动）

| 状态 | ID | 优先级 | 行动 | 验收 |
|---|---|---:|---|---|
| [ ] | `TASK-2F9C71B4A0` | P1 | 观测充分性建模 | 可判定体表各区域被哪些相机、在哪些时刻、以何有效分辨率观测；据此分配 Gaussian 容量并决定何时回退先验 |
| [ ] | `TASK-8D3E50CA16` | P1 | 跨相机 × 跨时刻观测聚合 | 同一行人在多相机多时刻的观测在 canonical space 中对齐聚合，量化其相对单视角的增益 |
| [ ] | `TASK-BF7204E9D3` | P1 | 接入人体/衣物先验模块 | LHM 类前馈先验或 garment 分解作为被调用模块补全观测不足区域，独立消融其贡献 |

## 待研究者确认的外部事项

- **作者位与分工**：本方向的技术核心（观测充分性、跨视角聚合、分层评测）在 3DGS/几何/评测侧；人体与衣物先验为被调用模块。若合作者期待一作，需在方法设计启动前谈定，可选方案为同批数据上的 garment 姊妹论文。
- **文献补漏**：在 Semantic Scholar 上按 human/pedestrian 过滤 OmniRe 的引用列表，核对是否已有改进其人体分支的工作。
- **数据许可**：nuScenes 使用需遵守其 terms of use。SMPL 权重受其许可限制，已加入 `.gitignore`，不得入库或转发。
- **分层评测的掩码来源**：当前用 `dynamic_masks/human`（3D box 投影，偏大）。`fine_dynamic_masks/human` 生成后是否切换，待研究者确认——切换会使人体像素边界更准，但也会改变分层统计。

## 已完成的项目治理

- [x] 竞争格局调研两轮，确认「可编辑可重打光驾驶场景」方向不可行，`IDEA-DC38D8C3CC41` 标记 `challenged`。
- [x] 驾驶场景行人重建 SOTA 地图建立，确认 human-region 存在度量空白。
- [x] 方向定位如实记录为「OmniRe 人体分支的改进」，非新方向。
- [x] 13 条新 `LIT-*` 登记；`IDEA-F1BED52F1B2D` 经两次演化收敛到实测支持的表述。

## 历史范围（FastRelight，2026-08-18，已不再作为主线）

原计划见 [`plans/2026-08-18_fastrelight_research_program_v1.md`](plans/2026-08-18_fastrelight_research_program_v1.md)；原实验 `EXP-1584B0636795`、`EXP-4C2A9AD4C3D2`、`EXP-54CD8F9137F2`、`EXP-C4E8F5217892` 保留为历史记录，保持 `blocked`。收缩原因见 [`plans/CHANGELOG.md`](plans/CHANGELOG.md)。
