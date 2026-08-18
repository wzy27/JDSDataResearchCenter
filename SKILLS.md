# Agent 能力目录

本仓库只保留直接支撑科研可追溯性的核心通用模块：

| 能力 | 用途 |
|---|---|
| `literature-intake` | 从 DOI、arXiv、OpenAlex 或 PMID 建立文献记录与证据卡片 |
| `idea-ledger` | 记录研究假设、替代方案、验证路径和演变历史 |
| `experiment-ledger` | 记录实验定义、代码/数据版本、preflight、运行与结果 |
| `experiment-watchdog` | 监控进程、日志、资源和输出门槛 |

PDF、Notebook、绘图、数据分析、可视化和 Zotero 等能力不再复制到仓库；需要时使用宿主能力，并把最终证据落回 `LIT-*`、`IDEA-*`、`EXP-*` 和 artifact 记录。

第三方代码或能力在引入前必须记录来源 commit、许可证和本地修改。本仓库当前没有 vendored 第三方 skill，见 [`.agents/skills.lock.json`](.agents/skills.lock.json)。
