# 计划版本日志

## 2026-08-18 — v1（当前）

- 从 Presentation 与 QE report 固化 FastRelight 的范围、组件、监督和评估锚点。
- 将当前阶段纠正为“总体设计完成，完整实现和规模验证未完成”。
- 首版输入锁定为 RGB + LiDAR；radar 延后到数据和收益明确后再决策。
- 建立 P0–P6、G0–G6 阶段门，优先得到可复现组件 baseline 和 CARLA 光照真值，而不是直接联合训练。
- 新增三条可证伪 IDEA、稳定 TASK ID 和 planned/blocked 实验记录。
- 锁定 DriveStudio `main@e59bda4f` 与 Humans4D 子模块，建立 sequence manifest schema；因缺 Linux/NVIDIA executor 和 Waymo 数据，P0 smoke 仍 blocked。
- 竞争检索确认 LightSim、DrivingGaussian++、MADrive、HorizonForge、DrivingEditor 等已覆盖总体目标；主方法收缩为动态跨组件 visibility/shadow transport。

后续版本不覆盖本文件对应计划；只有 baseline 复现结果、传感器决策或阶段门结论变化时才新增版本。
