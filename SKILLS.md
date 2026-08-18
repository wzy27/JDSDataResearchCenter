# Agent 能力目录

本仓库只直接保存体积可控、许可证明确、可离线审计且与科研工作高频相关的 skill。
依赖完整运行时、外部服务或大量二进制资源的能力优先通过插件提供，不整包复制进仓库。

## 仓库自研

| Skill | 用途 |
|---|---|
| `literature-intake` | 文献元数据、证据卡和稳定 `LIT-*` 记录 |
| `idea-ledger` | Idea、假设、替代方案、验证路径与演变记录 |
| `experiment-ledger` | 实验定义、运行、产物和 `EXP-*` 追溯 |

## 已引入的开源 skill

| Skill | 上游 | 许可证 | 用途 | 主要可选依赖 |
|---|---|---|---|---|
| `pdf` | `openai/skills` | Apache-2.0 | PDF 读取、生成与渲染检查 | `pdfplumber`、`pypdf`、`reportlab`、Poppler |
| `jupyter-notebook` | `openai/skills` | Apache-2.0 | 创建和整理实验分析 notebook | JupyterLab、IPython kernel |
| `matplotlib` | `tvhahn/matplotlib-skill` | MIT | 生成适合论文的 Matplotlib/Seaborn 图表并执行视觉 QA | Matplotlib、Seaborn、NumPy、Pandas |

精确上游 commit 与路径记录在 [`.agents/skills.lock.json`](.agents/skills.lock.json)。第三方 skill
保持原文和许可证；更新时先审计 diff、依赖与脚本，再修改 lock 文件。

## 运行时插件

这些能力安装在 Codex 宿主环境中，不复制到仓库。所需插件记录在
[`.agents/plugins.required.json`](.agents/plugins.required.json)；安装和登录状态属于本机状态，切换机器或新建环境后应重新核对。

| 能力 | 插件 | 当前接入结论 | 使用边界 |
|---|---|---|---|
| 统计分析、数据清洗、实验报告 | Data Analytics | 已安装并确认工具可调用 | 负责探索、统计和交互报告；最终指标仍应落到 `EXP-*` 及可追溯产物 |
| 交互式图表与可视化 | Visualize | 已安装 | 适合参数探索、关系说明和临时交互视图；论文静态图仍使用 `matplotlib` 并保存生成依据 |
| Zotero 文献库同步 | Zotero | 已安装；新会话加载 | 读取 collection、item 和附件元数据；写入项目前先确认目标 collection，不把凭据或私有附件 URL 写入仓库 |

推荐组合流程：

1. 从 Zotero 取回文献标识符与元数据，经 `literature-intake` 去重后生成 `LIT-*`；
2. 从实验产物读取结构化数据，由 Data Analytics 清洗、统计并形成初步报告；
3. 用 Visualize 做交互探索，用 `matplotlib` 生成可复现的论文静态图；
4. 把统计口径、输入数据版本、脚本或 notebook、图表产物反向链接到 `EXP-*` 与后续 `FIG-*` / `TABLE-*`。

插件可用不代表科研证据已经入账。任何要进入论文的数字、图表或结论都必须能回到原始数据、代码版本与实验记录。

## PPT / Excel 方案

当前宿主具备已连接文档的 Excel/PowerPoint 控制接口，但只有在用户打开并连接对应文档会话后才可用。这条路径适合编辑现有 Office 文件，不需要把 Office 自动化代码复制进仓库。

无连接会话时采用以下轻量兜底：

| 格式 | 候选 | 许可证 | 结论 |
|---|---|---|---|
| `.xlsx` / `.xlsm` | `openpyxl` | MIT | Windows/Python 可直接使用，适合读写工作簿；公式重算与最终视觉检查交给 Excel 或 LibreOffice |
| `.pptx` | `PptxGenJS` | MIT | 跨平台生成 OOXML，适合从结构化大纲生成可编辑幻灯片；只在实际任务中按项目安装，不提交 `node_modules` |
| `.pptx` | `python-pptx` | MIT | Python 环境较轻，适合模板填充和简单编辑；复杂布局与渲染 QA 能力弱于完整 PPT skill |

暂不自研 PPT/Excel skill。先用真实科研任务积累模板、错误样例和验收标准；当同一工作流稳定复用至少三次，再把最小适配层提炼为本仓库 skill。

## 暂缓引入

- Anthropic 的 `pdf/docx/pptx/xlsx` 文档 skill：相关仓库明确说明这四项是 source-available，
  不是开源；不作为本仓库的开源依赖。
- `presentation-skill`：MIT，但当前上游约 493 个文件、71 MB，并依赖 Node、PptxGenJS、
  LibreOffice/Poppler 等完整工具链。需要时优先以插件或独立工具仓使用，不直接膨胀控制仓。

## 引入门槛

新增第三方 skill 前至少确认：

1. 上游仓库、精确 commit 和许可证；
2. `SKILL.md`、脚本和安装命令已经人工审计；
3. 不读取或上传与任务无关的数据，不携带凭据；
4. Windows/Codex 路径和工具假设可满足；
5. 体积与依赖适合本控制仓；
6. 有最小 smoke test，且不会破坏现有科研追溯规则。
