# JDS Data Research Center

本仓库是 JDS 三维人体重建与自动驾驶场景研究的控制面和可追溯账本。它管理研究问题、文献、实验、代码版本与外部数据引用，不保存原始数据包、个人资料、模型权重或大体积实验产物。

接入本仓库的 Agent 必须先阅读 [AGENTS.md](AGENTS.md)。已安装和候选能力见 [SKILLS.md](SKILLS.md)。

## 当前项目

- [`projects/jds-3d-reconstruction/`](projects/jds-3d-reconstruction/)：围绕 LHM、动态人体 Gaussian、服装形变与自动驾驶场景数据开展研究管理。
- 外部数据源：`s3://bucket-2622-guiyang/w84400451/jds_data/`。
- 2026-08-18 已完成首次只读盘点：3 个对象，共 3,492,821,998 字节；对象哈希和脱敏概览见项目目录。

## 仓库边界

- Git 中只保存小体积、可审计的结构化记录、计划、来源说明和校验信息。
- S3/OBS 继续保存 PPTX、ZIP、视频、图片、数据集和其他大文件。
- 从外部归档导入代码前，必须先确认来源、许可证和基准 commit；不把工作站备份整体复制进 Git。
- 已发现的个人/行政文件只记录为风险类别，不记录具体内容，也不进入仓库。

## 通用能力

本仓库从 `wzy27/ResearchCenter` 的已提交版本提取以下与具体项目无关的模块：

- `.agents/skills/`：文献、Idea、实验账本以及 PDF、Notebook、Matplotlib 工作流。
- `experiment-watchdog/`：实验进程、日志、资源和产物门槛监控。
- `.agents/skills.lock.json` 与 `.agents/plugins.required.json`：第三方能力来源和运行时插件声明。

未复制源仓库中的任何 `projects/*`、机器本地配置、测试文件或未跟踪数据。
