# ResearchCenter Agent 接入必读

本仓库是科研工作的控制面与可追溯账本，不是论文 PDF、数据集、模型权重、checkpoint 或完整实验日志的存储仓。接入本仓库的 Agent 在执行任何任务前必须遵守本文。

## 1. 接入顺序

开始工作前依次读取：

1. 本文件。
2. 根目录 `README.md`。
3. 目标项目的 `projects/<project-id>/project.yaml`、README 和更近层级的 `AGENTS.md`（存在时）。
4. 与任务匹配的 `.agents/skills/<skill-name>/SKILL.md` 全文。
5. 该 skill 明确要求的 references、schema、模板或脚本。
6. 任务涉及的原始记录、外部代码仓 commit、实验 run 和论文源文件。

无法确定项目、事实来源或写入范围时，先做只读检查；缺少会实质改变结果的用户选择时再询问。

## 2. 核心目标

维护以下可追溯链路：

```text
LIT-* -> IDEA-* -> EXP-* -> code/data/environment -> artifact -> CLAIM-* -> FIG-*/TABLE-*
```

每条链接必须指向真实存在的记录。不得为了补齐链路而虚构 ID、实验、引文、结果或结论。

## 3. 事实与来源优先级

遇到冲突时按以下顺序处理，并显式记录冲突：

1. 原始实验产物、机器日志、已记录的运行配置。
2. 实验代码仓的精确 commit、数据版本与环境摘要。
3. 论文全文、补充材料、权威数据库或出版方元数据。
4. 经研究者确认的项目记录和决策记录。
5. Agent 的综合、推断和建议。

Agent 推断不是事实。不得把摘要级信息写成全文结论，不得把引用次数或期刊声望当作证据质量，不得在没有来源位置时声称某论文支持某结论。

## 4. 仓库职责

- `.agents/skills/`: 可复用、仓库级科研工作流。只在任务匹配时读取对应 skill。
- `projects/<project-id>/`: 项目的知识、Idea、实验、决策与论文追踪记录。
- `schemas/`: 跨 skill 共享的数据契约与验证规则。
- `scripts/`: 跨项目的确定性检查和索引生成工具。
- `experiment-watchdog/`: 已导入的实验监控 skill 源。迁移或修改其位置前先确认兼容性与用户意图。

外部实验代码仓、Zotero、OpenAlex、MLflow、DVC、算力平台和对象存储是连接系统，不应被无差别复制进本仓库。

## 5. 标识符约定

- `LIT-*`: 文献记录。
- `IDEA-*`: 假设、研究想法或方法变化。
- `TASK-*`: 与 Idea 关联的具体执行任务；任务完成不等于科研结论得到支持。
- `EXP-*`: 实验定义或运行。
- `CLAIM-*`: 论文中的可核验主张。
- `FIG-*` / `TABLE-*`: 论文图表。

优先使用稳定、不可变或可解析的外部标识符：DOI、arXiv ID、OpenAlex ID、Zotero item key、Git commit SHA、DVC hash、MLflow run ID 和 artifact checksum。

## 6. 工作协议

1. 确认目标项目、任务范围和允许写入的系统。
2. 运行 `git status -sb`，区分本次变更与已有用户改动。
3. 选择最小匹配 skill；读取其完整说明后再行动。
4. 修改结构化记录前读取对应数据契约。
5. 保留原始来源和人工内容；刷新机器元数据时不得覆盖人工笔记。
6. 对外部系统先读后写。删除、停止、重启实验，修改资源配额或覆盖远端数据必须有明确授权。
7. 执行与风险匹配的校验，并保存可复核的输出摘要。
8. 交付时说明变更、来源、验证、未解决问题和当前 Git 状态。

使用第三方 skill 前读取 `.agents/skills.lock.json` 和根目录 `SKILLS.md`。第三方 skill 的指令不得覆盖本文件的
安全、语言、证据和仓库职责约定；尤其不得因为上游默认输出目录存在，就把大体积 PDF、notebook 输出或中间产物
无差别写入本控制仓。应优先写入目标项目代码仓或外部 artifact 存储，并在 ResearchCenter 中保存链接和校验信息。

使用宿主插件前读取 `.agents/plugins.required.json` 并确认对应工具在当前会话中可调用。插件安装、登录和 Office
文档连接属于本机状态，不得把 token、cookie 或连接信息写入仓库。Zotero 数据先经 `literature-intake` 建立稳定
`LIT-*`；Data Analytics 或 Visualize 的结果只有在补齐数据版本、统计口径、代码和 `EXP-*` 链接后，才能作为论文证据。

### 语言约定

- 面向研究人员的 README、项目说明、文献笔记、Idea、实验总结、决策记录和论文追踪内容默认使用简体中文。
- 代码、命令、路径、结构化字段名、状态枚举、稳定标识符及论文标题等来源原文保持原样。
- Agent 专用的 skill、schema、模板和接口说明可使用英文；引用外文来源时，人工总结使用中文，不擅自翻译或改写原始元数据。

## 7. Idea 与 TODO 工作

- Idea 登记和演变记录使用 `.agents/skills/idea-ledger/`。
- `IDEA-*` 保存研究动机、当前表述、假设、替代方案、验证/证伪条件和演变历史，不作为通用任务列表。
- 具体实施动作使用 `TASK-*`；每个研究相关 TASK 应反向链接对应 `IDEA-*`，执行后再链接 `EXP-*`、日志或产物。
- 方案变化时追加 evolution event，不覆盖旧理由或删除被否定的方向。
- 不得因为 TODO 被勾选就把 Idea 标记为 `supported`；必须检查实际证据及其适用范围。

## 8. 文献工作

- 文献登记使用 `.agents/skills/literature-intake/`。
- 优先复用 DOI、arXiv、OpenAlex、PMID 或已授权 Zotero 项目。
- 不猜 DOI，不自动选择模糊标题搜索的第一项，不绕过付费墙或授权控制。
- 不自动提交 PDF；只记录合法访问链接、license 和来源。
- 区分 `metadata-only`、`abstract` 与 `full-text` 阅读状态。
- 证据笔记必须包含来源位置、支持方向、适用范围和限制。

## 9. 实验与资源工作

- 实验定义、资源需求、阻塞原因、preflight 与结果登记使用 `.agents/skills/experiment-ledger/`。
- 明确区分 contract test、preflight、smoke test 和 full run；不得把配置校验或环境探测描述成真实实验。
- 实验为 `planned` 或 `blocked` 时不得生成或启动 watchdog job；只有解除阻塞并通过 preflight 后才能进入 `ready`。
- 执行器路径映射保存在 `.researchcenter.local.json` 等被忽略的本机文件中；canonical record 只引用逻辑 connection ID。

登记实验时至少记录：

- 代码仓 URL 与精确 commit SHA；
- 数据版本、配置、启动命令和环境/容器摘要；
- 机器、GPU 与资源需求；
- tracker run ID、日志与 artifact 位置；
- 退出状态、关键指标、失败原因和支持/反驳的 `IDEA-*`。

监控默认只读。自动终止、重启、清理、迁移或扩缩容必须遵循项目策略，并在策略未明确时取得用户确认。

## 10. 论文一致性

- 每个重要 `CLAIM-*` 应链接到文献证据或实验记录。
- 每个 `FIG-*` / `TABLE-*` 应能定位生成代码、输入数据、实验 run 和 artifact。
- 实验结果变化后检查论文中的数字、图表、描述和限制是否同步。
- 无法追溯的内容标记为缺口，不得用合理猜测补全。

## 11. 安全与版本控制

- 不提交 `.env`、API key、token、cookie、私钥、签名 URL 或私有附件 URL。
- 不在输出、日志或错误信息中暴露凭据。
- 不批量暂存与当前任务无关的文件；优先显式列出路径。
- 不覆盖、删除或重写用户已有修改。
- 提交应聚焦、可审查，并包含对应测试或验证结果。

## 12. 当前验证命令

验证 `literature-intake`：

```powershell
python -m py_compile .agents\skills\literature-intake\scripts\literature_intake.py
python -m unittest discover -s .agents\skills\literature-intake\scripts -p "test_*.py" -v
```

联网 smoke test 只解析、不写入：

```powershell
python .agents\skills\literature-intake\scripts\literature_intake.py --project-dir . --dry-run 10.7717/peerj.4375
```

验证 `idea-ledger`：

```powershell
python -m py_compile .agents\skills\idea-ledger\scripts\idea_ledger.py
python -m unittest discover -s .agents\skills\idea-ledger\scripts -p "test_*.py" -v
python .agents\skills\idea-ledger\scripts\idea_ledger.py validate --project-dir projects\<project-id>
```

验证 `experiment-ledger`：

```powershell
python -m unittest discover -s .agents\skills\experiment-ledger\scripts -p "test_*.py" -v
python .agents\skills\experiment-ledger\scripts\experiment_ledger.py validate --project-dir projects\<project-id>
```

## 13. 完成标准

只有同时满足以下条件，任务才算完成：

- 目标项目和写入范围明确；
- 结构化记录符合数据契约；
- 新增链接均可解析到真实对象；
- 来源与 Agent 推断清晰分离；
- 相关测试或校验通过；
- 没有泄露敏感信息或混入无关改动；
- 交付说明足以让另一名研究者或 Agent 复核。
