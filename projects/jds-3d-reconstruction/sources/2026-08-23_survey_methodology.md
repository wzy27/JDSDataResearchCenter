# 文献调研方法论

> 由 2026-08-23 漏检 Hierarchy UGP (ICCV 2025) 一事确立。该文标题不含 pedestrian、human、SMPL
> 任何一词，其行人区域指标位于 Table 2，摘要亦未提及；纯主题关键词检索**结构性地**无法发现它。

## 0. 核心原则

**相关的工作不一定使用你的词汇。** 一篇解决行人重建问题的论文，可以通篇称之为「非刚性动态元素」或「统一原语」。因此：

> 标题与摘要检索用于**发现**，全文正查用于**判定**。二者不可互相替代。

## 1. 四条必做通道

任何一次「这个方向有没有人做过」的判断，须同时走完四条通道，缺一不可。

### 通道 A：会议全量枚举 + 全文正查

对每届相关会议（ICCV / CVPR / ECCV / NeurIPS / WACV / ICLR）：

1. 抓取整届论文标题与 PDF 链接；
2. 用**宽松**的领域词粗筛（Gaussian、splatting、NeRF、driving、urban、street、dynamic scene、human、avatar…）——宁可多下几十篇；
3. 下载粗筛通过者的 PDF，抽取全文；
4. 用**精确**的探针词在全文中计分（pedestrian、SMPL、human region、PSNR*、OmniRe、DeformableNodes…）；
5. 对报告了分区指标的强信号（`pedestrian region`、`PSNR\s*\*`、`metrics for the pedestrian`）加重权。

工具：[`../tools/survey.py`](../tools/survey.py)。

**这条通道是本次漏检的直接补救，优先级最高。**

### 通道 B：引文图谱遍历

对锚点论文（本项目为 OmniRe、Street Gaussians、3DGS）取其**前向引用**列表，按人体/行人相关词过滤。

关键词检索按主题相似度排序，引文图谱按学术承继关系排序——两者的召回集不同。凡是改进锚点论文的工作，必然引用它。

**该通道当前依赖研究者手动在 Semantic Scholar 执行**，本地工具尚未覆盖。

### 通道 C：主题关键词检索（含同义词扩展）

传统检索，但须做词汇扩展。对每个核心概念列出至少三种可能的表述：

| 我们的说法 | 别人可能的说法 |
|---|---|
| 行人重建 | non-rigid dynamic element、deformable actor、articulated object、unified primitive |
| 观测不足 | sparse observation、low-resolution、long-range、distant object、partial visibility |
| 容量分配 | densification、level of detail、adaptive primitive、budget |
| 姿态门 | template-free、annotation-free、without SMPL、prior-free |

### 通道 D：负向检索

**对我们打算写进论文的每一条主张，专门检索它的反例。** 不是找支持自己的证据，而是找推翻自己的证据。

本项目应持续负向检索的主张：

- 「无人报告 human-region 分区指标」→ 检索 `pedestrian region metrics`、`per-class PSNR driving`
- 「无人按观测充分性分配容量」→ 检索 `adaptive gaussian budget`、`LOD dynamic actor`
- 「无人量化可重建边界」→ 检索 `reconstructibility`、`observability analysis reconstruction`

## 2. 每条命中必须记录的字段

| 字段 | 为何必要 |
|---|---|
| 会议与年份 | 本次漏检的部分原因是过度偏重 arXiv 与 2026，忽略 2025 年会议论文集 |
| 是否报告分区/分类指标 | 决定它是否与我们的度量主张冲突 |
| 是否使用人体模板 | 决定它是否已拆掉「姿态门」 |
| **代码是否已发布** | 决定它是可运行 baseline，还是只能做 component-level proxy。须核对仓库实际内容与最后 push 时间，不能只看论文里的 "we plan to release" |
| 其自述的局限 | 通常即我们的机会所在 |
| 与我们主张的冲突点 | 必须逐条列出，不得回避 |

## 3. 触发时机

- 选题确立前——必做全部四条通道；
- **每次主张发生实质变化时**——重做通道 D；
- 每个新会议周期（ICCV/CVPR/NeurIPS 放榜后）——重做通道 A；
- 投稿前——全部重做。

## 4. 工具的验收标准

**任何调研工具在使用前，必须先证明它能命中已知被漏掉的论文。** 具体到本项目：`survey.py` 在 ICCV 2025 上必须命中 Hierarchy UGP，否则其「未发现相关工作」的结论不得采信。

这条规则的一般形式是：**用已知的失败案例做回归测试。** 一个从未被验证过召回能力的检索流程，其阴性结果没有证据价值。

## 5. 本方法论无法覆盖的部分

- **未公开的在研工作**。任何检索都无法发现尚未公开的竞争工作，该风险不可消除，只能通过缩短周期缓解。
- **非英文文献**。
- **通道 B 当前需手动执行**，尚未自动化。
- 全文抽取依赖 PDF 文本层，扫描版或图片化表格会被漏掉。
