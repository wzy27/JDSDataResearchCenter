# JDS 三维人体重建与自动驾驶场景研究

## 当前判断

现有材料聚焦于把单图人体重建与可动画 Avatar 引入自动驾驶/街景 3DGS 场景，并处理动态人体的光照、LBS、服装形变和遮挡问题。这个表述是根据 2026-08-18 的 S3 材料盘点作出的研究方向归纳，不等同于已经验证的科研结论。

## 已确认的来源事实

- S3 前缀包含一个 24 页周会 PPTX 和两个 ZIP，共 3,492,821,998 字节。
- PPTX 涉及 Large Human Model、SAM3D、Light-X、Anix、HRM2Avatar、LHM/Lighting/Scene Gaussian/LBS，以及 Argoverse2、CARLA、DriveStudio、NuScenes。
- PPTX 给出的数据需求覆盖合成与真实数据、场景与路线、多时段光照、行人与车辆 ID 跟踪、3D 包围框、天气条件和连续帧可见性。
- `Transfer_Data.zip` 的研究代码主体是 LHM 及其依赖；`download.zip` 包含行人轨迹、评测视频、研究补丁和分析材料，同时混有运行环境、个人与行政资料。
- 归档中的一份分析指出：固定地把 seam-close/stretch 位置写回动态 Gaussian 中心，可能改善大幅腿部动作时的裙摆分裂，但在较小动作下造成内缩；建议使用动作相关的连续强度。该结论仍需在可追溯实验中复现。

## 管理原则

- 以 S3/OBS 为大文件事实源，以 SHA-256 和对象 URI 建立引用。
- 先完成隐私、许可证和代码来源清理，再选择性导入研究代码。
- 每个实验记录精确代码 commit、数据版本、命令、环境、输出位置和失败原因。
- 不把 PPTX、ZIP、视频、图片、模型权重、邮件或行政文件提交到 Git。

## 入口

- [`artifacts/s3_inventory.json`](artifacts/s3_inventory.json)：S3 对象级清单与哈希。
- [`sources/2026-08-18_s3_intake.md`](sources/2026-08-18_s3_intake.md)：首次材料盘点、事实/推断边界和风险。
- [`TODO.md`](TODO.md)：下一步清理与复现实验任务。
