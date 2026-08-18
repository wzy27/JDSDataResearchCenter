# TODO

## P0：恢复可复现基线

- [ ] 确认实际使用的 OmniRe/DriveStudio 仓库 URL、commit、配置分支和本地补丁。
- [ ] 从混合 ZIP 中只白名单提取研究代码、配置、日志与指标，排除个人/行政/邮件/安装包。
- [ ] 为现有 `Background`、`SMPLNodes` 和组合视频补齐 scene ID、命令、checkpoint 与代码版本。
- [ ] 在一个小型 Waymo scene 上分别导出 background、vehicle、human 和 composite 四层结果。

## P1：三类重建独立验收

- [ ] 人体：去除行人 ID、路径和模型名硬编码，完成 Gaussian rotation/LBS 传播。
- [ ] 人体：比较 StageA final 与 step 7000，并完成多 subject、多动作和多服装验证。
- [ ] 车辆：恢复 OmniRe rigid actor 基线，记录独立 PSNR/SSIM/LPIPS、几何与轨迹误差。
- [ ] 场景：恢复 background 基线，记录 novel-view、深度/几何和跨时段稳定性。

## P2：统一编辑与重打光

- [ ] 定义统一 actor 接口：canonical geometry、pose/rigid transform、material、visibility 和 light response。
- [ ] 实现人/车/场景的独立选择、替换、移动、驱动和组合。
- [ ] 把光照数据的含义、维度、生成方式和 train/test 划分补齐。
- [ ] 实现 albedo/material 与 lighting/shading 分解，以及 cast shadow/visibility。
- [ ] 建立同光照重建、跨光照 relight、跨实体阴影一致性和编辑后真实性评测。

## 已完成的整理工作

- [x] 只读列举 S3 前缀并记录 3 个对象的大小和 SHA-256。
- [x] 读取 PPTX、ZIP 和关键嵌套包，形成不含个人内容的进度审计。
- [x] 将大文件、个人资料、安装包和环境快照排除在 Git 仓库之外。
