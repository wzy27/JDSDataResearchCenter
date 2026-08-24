# 双表示互导优化的成立条件

## 研究问题

3DGS 与隐式表面（SDF）互相引导优化已是表面重建的常见范式：GS-Octree、MGSR、GSDF、
NeuSG、3DGSR 都属此列。但**耦合本身的性质从未被研究**——两条通道该多强、方向该如何、
何时反而有害，各方法各取一组启发式常数了事。

> **两种表示互相引导时，耦合的强度与方向如何决定结果？现有方法取的值是最优的吗？**

方法侧重点是耦合通道的强度—效果关系、失效机制的定位与修正；
表示本身（2DGS/3DGS/八叉树 SDF）作为被调用模块，不作为主创新。

## 定位（必须如实表述）

**本方向不是新方向，是对 MGSR 与 GS-Octree 所属范式的机制性追问。**
现状、证据与局限见 [`STATUS.md`](STATUS.md)。

支撑该方向成立的三点：

1. **现象由导师论文自己报告，但未被解释。** MGSR 消融表 Model K vs M 显示双向 BP
   全面劣于单向（PSNR 36.64 vs 37.69），解释只有一句
   "bidirectional BP influences optimization of the branch which provides supervision"，
   随后用 stop-gradient 绕过。**现象的存在性无需我们证明，我们做它缺的那一半。**
2. **增益不在重建侧。** MGSR 无互导对完整：PSNR +2.59 dB，而 NC 仅 90.16→90.60、
   CD 仅 0.92→0.90。**互导主要在提升渲染，几何几乎没动**——导师要求做重建方向，
   而重建恰是这套机制留下空间最大的地方。
3. **文献位置已核验。** 188 篇引文图全文 + 一篇专门综述全文（90269 字符，
   收敛性论述 0）。最接近的四篇（GEAR / CarGS / MooMIns / Beyond Heuristics）
   各差一步，详见 [`STATUS.md`](STATUS.md) §3.1。

**风险：** 效应幅度需足够大。当前实测 ref 支 5.4%、geo 支 0.91%，
噪声地板 0.36%——幅度成立，但**仅单场景**。跨场景不成立则方向需重估。

## 当前阶段

首批实验已完成并经三种子重复确认（[`STATUS.md`](STATUS.md) §3.3）：

| 结论 | 状态 |
|---|---|
| 噪声地板 0.36%（ref）/ 0.38%（geo），n=3 | 已确立 |
| 加强 geo→ref 耦合：ref 支劣化 5.4%，geo 支改善 0.91%，**方向相反** | 已确立 |
| `w_depth=0.05` 处存在内部最优（−3.6%） | n=1，复现中 |
| 劣化机制为 depth 的 max 归一化 | 未验证（E-β′） |

**判据：** 内部最优点若在三种子上成立且幅度 ≥2%，则「MGSR 的取值不是最优」
可直接写入论文；机制若经 E-β′ 确认，则贡献从「发现现象」升为「给出原因与修法」。

## 数据与基线

- 代码：MGSR（可完整运行，DTU scan24 三阶段 2h07m）、GS-Octree（受阻，见 [`STATUS.md`](STATUS.md) §6）。
- 数据：DTU scan24。真值 `stl024_total.ply` 与 ObsMask 经 `tools/zip_partial.py`
  局部抽取取得（**141 MB 换掉 14 GB**）。
- 评测：DTU 官方协议，实现于 [`tools/dtu_eval.py`](tools/dtu_eval.py)，含坐标系自检。
- 执行器：`wsl2-ubuntu2404-rtx4090`，环境构建与偏离见
  [`sources/2026-08-23_executor_environment_build.md`](sources/2026-08-23_executor_environment_build.md)。

**六处公开产物不完整**（其中三处直接改变数值结果）使论文数字无法复现，
**故所有对照组必须是我们自己跑出的基线**。详见
[`sources/2026-08-24_mgsr_code_audit.md`](sources/2026-08-24_mgsr_code_audit.md)。

## 项目入口

- [`STATUS.md`](STATUS.md)：**现状唯一入口**，只写当前成立的结论。
- [`TODO.md`](TODO.md)：带稳定 TASK ID 的执行视图。
- [`sources/2026-08-24_mutual_guidance_position.md`](sources/2026-08-24_mutual_guidance_position.md)：
  立论与证伪设计，按节追加，**含三次公开修正**（§9 / §11 / §15）。
- [`sources/2026-08-24_mgsr_code_audit.md`](sources/2026-08-24_mgsr_code_audit.md)：
  代码审计、环境构建、互导环逐行结构。
- [`sources/2026-08-23_survey_methodology.md`](sources/2026-08-23_survey_methodology.md)：
  调研方法论与七次证伪的教训。
- [`progress.md`](progress.md)：既有资产审计。

## 历史范围

本项目经两次转向，原产出均保留复用：

**FastRelight（2026-08-18，已终止）** — 可编辑、可重打光的 4D 驾驶场景重建。
终止原因见 [`plans/CHANGELOG.md`](plans/CHANGELOG.md)：整体方向已被 LightSim、
DrivingGaussian++、MADrive 等占据；且导师要求成果落在重建方向，重打光属渲染贡献。

**驾驶场景行人重建（2026-08-23，已终止）** — 观测受限条件下的行人重建。
终止原因：Hierarchy UGP (ICCV 2025) 已取得 human-region +8 dB；目视核验确认被丢弃的
行人绝大多数确属信息不足，明确的模型失败仅 1/53。保留复用的资产：观测充分性分析、
分层评测器、`gpu-budget` skill。

## 仓库边界

原始文档、S3 数据、视频、数据集、模型权重和训练输出不进入 Git。
完成项必须能追溯到代码 commit、数据 manifest、命令、环境、指标和产物；
只有架构图、文件名或渲染视频不能标记为「已完成」。
