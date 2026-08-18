# 基于 OmniRe 的可编辑城市重建与重打光

## 目标

以 OmniRe 的动态 Gaussian scene graph 为基线，把城市驾驶日志分成四类可控表示：

1. 静态场景；
2. 刚性车辆；
3. 非刚性人体/行人；
4. 独立于几何与材质的光照表示。

最终系统应能替换、移动或驱动人和车，编辑场景，并在改变时间、天气或光源后重新生成光照一致的结果。

## 当前状态

整体处于“人体原型已有实验，其他主线证据不足”的阶段：

- 人体：已有 LHM/SMPL Gaussian 注入、动态服装实验和可量化 StageA 结果，但工程仍是硬编码原型。
- 场景：存在 Background 训练视频产物，但缺少配置、日志、checkpoint 和质量指标。
- 车辆：S3 材料中没有可审计的车辆重建实现或实验。
- 重打光：只有少量光照系数数据和运行时开关痕迹，没有完整材质/光照分解与验证。
- 编辑合成：已能尝试替换指定行人 Avatar，但没有通用的人/车/场景编辑接口。

详细证据、完成项和阻塞项见 [`progress.md`](progress.md)。

## 仓库边界

- 原始 S3/OBS 归档、视频、数据集和模型权重不进入 Git。
- 代码只有在确认来源仓库、基准 commit、许可证和补丁顺序后才选择性导入。
- 每个完成项必须有可复现命令、配置、数据版本、指标和产物链接；仅有视频文件名不视为完成。

## 入口

- [`progress.md`](progress.md)：五条工作线的进度判断。
- [`artifacts/s3_inventory.json`](artifacts/s3_inventory.json)：S3 对象级清单与哈希。
- [`sources/2026-08-18_omnire_basis.md`](sources/2026-08-18_omnire_basis.md)：OmniRe 基线与本项目扩展边界。
- [`sources/2026-08-18_s3_intake.md`](sources/2026-08-18_s3_intake.md)：首次材料盘点。
- [`TODO.md`](TODO.md)：按优先级整理的下一步。
