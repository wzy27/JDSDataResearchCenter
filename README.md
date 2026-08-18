# JDS Data Research Center

本仓库是基于 OmniRe 的可编辑城市重建与重打光研究控制面。目标是分别重建人、车和静态场景，再通过统一的重打光模块合成可编辑且光照可信的动态城市结果。

接入本仓库的 Agent 必须先阅读 [AGENTS.md](AGENTS.md)。已安装和候选能力见 [SKILLS.md](SKILLS.md)。

## 当前项目

- [`projects/jds-3d-reconstruction/`](projects/jds-3d-reconstruction/)：OmniRe 基线、人/车/场景分解重建、重打光和统一编辑。
- 外部数据源：`s3://bucket-2622-guiyang/w84400451/jds_data/`。
- 2026-08-18 已完成首次只读盘点：3 个对象，共 3,492,821,998 字节；这些对象不进入 Git。
- 当前进度结论：人体原型最深入；场景只有不可追溯的视频产物；车辆和重打光尚无完整实现证据。

## 仓库边界

- Git 中只保存小体积、可审计的结构化记录、计划、来源说明和校验信息。
- S3/OBS 继续保存 PPTX、ZIP、视频、图片、数据集和其他大文件。
- 从外部归档导入代码前，必须先确认来源、许可证和基准 commit；不把工作站备份整体复制进 Git。
- 已发现的个人/行政文件只记录为风险类别，不记录具体内容，也不进入仓库。

## 通用能力

本仓库从 `wzy27/ResearchCenter` 的已提交版本提取以下与具体项目无关的模块：

- `.agents/skills/`：文献、Idea 和实验账本。
- `experiment-watchdog/`：实验进程、日志、资源和产物门槛监控。
- `.agents/skills.lock.json` 与 `.agents/plugins.required.json`：能力来源和运行时插件声明。

未复制源仓库中的任何 `projects/*`、机器本地配置、测试文件或未跟踪数据。
