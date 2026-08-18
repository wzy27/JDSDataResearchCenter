# OmniRe 基线与本项目扩展边界

## OmniRe 提供的基线

OmniRe（ICLR 2025 Spotlight）以动态 Gaussian scene graph 重建城市驾驶日志，在不同局部 canonical spaces 中表示背景和动态 actor。官方项目页给出的核心划分是：

- 车辆：静态 Gaussians，加刚体变换产生运动；
- 近距离行人：基于 SMPL 模板拟合，支持关节级控制；
- 远距离或无模板动态 actor：使用自监督 deformation fields；
- 背景与各 actor 共同进入统一场景图，可用于实时仿真和场景编辑。

来源：

- 项目页：https://ziyc.github.io/omnire/
- 论文：https://arxiv.org/abs/2408.16760
- 官方实现：https://github.com/ziyc/drivestudio
- ICLR 2025：https://openreview.net/forum?id=9cwxZxJixB

## 本项目增加的目标

OmniRe 解决的是完整动态城市重建和 actor 级仿真。本项目在此基础上增加两项要求：

1. 人、车、静态场景必须能分别训练、导出、替换和组合；
2. 几何/材质与光照应解耦，使编辑后的实体在目标环境中接受一致的光照、可见性和阴影。

因此“重打光”不能只等价于调整 Gaussian SH 颜色。它需要明确的材质/反照率、光照条件、可见性/阴影和跨实体合成策略，并用未见光照与编辑场景验证真实性。

## 验收分层

- Level 1：分别复现 background、vehicle、human 基线。
- Level 2：三类表示可独立导出、替换和重新组合。
- Level 3：在原始光照下复合结果与输入一致。
- Level 4：在新光照下，人/车/场景的明暗、颜色、阴影和遮挡一致。
- Level 5：编辑后的动态序列在时间上稳定，并保持可实时或接近实时渲染。
