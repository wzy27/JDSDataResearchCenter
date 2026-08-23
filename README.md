# JDS Data Research Center

本仓库是基于 OmniRe 的可编辑城市重建与重打光研究控制面。目标是分别重建人、车和静态场景，再通过统一的重打光模块合成可编辑且光照可信的动态城市结果。

接入本仓库的 Agent 必须先阅读 [AGENTS.md](AGENTS.md)。已安装和候选能力见 [SKILLS.md](SKILLS.md)。

## 当前项目

- [`projects/jds-3d-reconstruction/`](projects/jds-3d-reconstruction/)：观测受限条件下的驾驶场景行人重建。2026-08-23 由原 FastRelight（可编辑可重打光的 4D 驾驶场景）收缩而来，原因见该项目的 `plans/CHANGELOG.md`。
- 外部数据源：`s3://bucket-2622-guiyang/w84400451/jds_data/`。
- 2026-08-18 已完成首次只读盘点：3 个对象，共 3,492,821,998 字节；这些对象不进入 Git。
- 当前进度结论：人体原型最深入；场景只有不可追溯的视频产物；车辆和重打光尚无完整实现证据。
- 2026-08-23 已建立可运行执行器（WSL2 + RTX 4090），完成 nuScenes v1.0-mini 预处理与行人观测条件审计。

## 仓库边界

- Git 中保存小体积、可审计的结构化记录、计划、来源说明、校验信息，以及**产出这些证据的分析与预处理脚本**（`projects/*/tools/`、`.claude/skills/`）。脚本入库的理由是证据可复现；脚本内不得有硬编码绝对路径，执行器侧路径以环境变量覆盖。
- S3/OBS 继续保存 PPTX、ZIP、视频、图片、数据集和其他大文件。
- 从外部归档导入代码前，必须先确认来源、许可证和基准 commit；不把工作站备份整体复制进 Git。
- 已发现的个人/行政文件只记录为风险类别，不记录具体内容，也不进入仓库。

## 通用能力

本仓库从 `wzy27/ResearchCenter` 的已提交版本提取以下与具体项目无关的模块：

- `.agents/skills/`：文献、Idea 和实验账本。
- `experiment-watchdog/`：实验进程、日志、资源和产物门槛监控。
- `.agents/skills.lock.json` 与 `.agents/plugins.required.json`：能力来源和运行时插件声明。

未复制源仓库中的任何 `projects/*`、机器本地配置、测试文件或未跟踪数据。
