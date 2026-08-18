# FastRelight 来源摘录：Presentation 与 QE report

## 来源与完整性

| 来源 | SHA-256 | FastRelight 位置 |
|---|---|---|
| `D:\Workspace\Presentation_0413_v3.pptx` | `df2202e92d58e760cea21023cda62e40280aac703a5d7356d843f77e147a30ab` | slides 25–32、41、43、45、49 |
| `D:\Workspace\QE_main.pdf` | `671fa520fa1d8e61ac6da556682b559e37358d466daf1182a33d9a87132084c1` | physical pages 44–55（Chapter 4），physical page 71（§6.2.3） |

两份文件由研究者提供，仅保留摘要和定位信息；原文件不进入仓库。

## 材料明确陈述的内容

### 问题与输入输出

- 目标是驾驶场景中的对象级编辑和重打光：移动行人/车辆、静态背景与天空需要显式分开，同时在类似光照下保持视觉一致（PPT slides 25–27；QE pp.44–46）。
- 输入为同步多视角 RGB 与主动深度。PPT slide 27 写作 “radar/LiDAR”，方法图与 QE Chapter 4 主要写 `RGB + LiDAR`，QE §6.2.3 又写 radar；该差异不能静默合并。
- 输出是显式前景/背景分解的 4D Gaussian 表示，支持对象移除、替换、运动修改和环境光改变（PPT slide 27；QE pp.44–46）。

### 组件化表示

- 静态背景：time-invariant feed-forward 3DGS，并用纹理补充未观测区域（QE pp.48–49）。
- 车辆：canonical Gaussian 集合加共享刚体变换 `R_t, T_t`（QE p.48）。
- 行人：canonical Gaussian、SMPL joints 和 LBS（QE p.48）。
- 通用形变体：自由的时变 Gaussian 位置/协方差，用于骑行者等难以归入单一人体或刚体的对象（QE p.49）。
- 天空：环境纹理；光照条件以环境光表示（PPT slide 29；QE Figure 4.1）。

### 重打光与训练

- 光照表示由跨组件共享的环境光参数和空间分区光照条件组成，后者意在表达建筑阴影与局部光源（QE p.50）。
- 轻量重打光模块直接作用于 Gaussian 属性和材质特征，并使用车辆/行人的类别材质先验（QE p.50）。
- 训练监督包括多视角 RGB、LiDAR depth、动态区域、时序一致性和补全背景；总损失为重建、几何、时序与正则项的加权和（QE pp.50–51）。
- 正则项用静态/动态估计光照梯度的点积约束光照泄漏，但材料没有给出它能唯一解决泄漏的证据（QE p.51）。

### 评估设计

- CARLA 提供可控光照、天气和交通，可作为跨光照定量真值（QE pp.52–53）。
- Waymo、nuScenes、Argoverse 2 用于真实场景，但没有重打光真值（PPT slide 30；QE pp.52–53）。
- 已提出的指标包括 PSNR/SSIM/LPIPS、时序 LPIPS 或 flow-aligned photometric error、LiDAR depth/normal consistency，以及编辑与重打光的定性一致性（PPT slide 30；QE pp.52–53）。
- 候选对比包括 UniSplat、Omni-Scene、EVolSplat、DriveGen3D、VR-Drive 和 DiST-4D；正式实验前需逐项核对代码、输入协议与可比较性（QE p.54）。

## 进度事实

QE physical page 71 的 §6.2.3 是当前最明确的状态声明：总体 pipeline design 已建立，后续工作是完整实现、动态重建与重打光联合优化、传感器接入和规模化验证。因此：

- 可以标记为完成：问题定义、总体架构、组件类别、初步损失和评估方向。
- 不可标记为完成：feed-forward 实现、五类组件集成、物理重打光、联合训练、CARLA/真实数据主表或论文结论。
- S3 中的人体 StageA 结果是可复用原型证据，不等价于 FastRelight 系统已实现。

## 材料自己暴露的问题

PPT slide 49 明确列出四个阻塞点：

1. 补全背景监督弱且跨时间不一致；
2. 动态对象重叠会造成实例混合，单靠 inpainting 无法分离；
3. 阴影区域难以分割，导致重打光不完整；
4. 纯 Gaussian 表示缺乏未观测区域信息，环境光估计不足。

此外，当前文档还没有锁定：feed-forward 网络结构与训练集、材质参数化、全局/局部光照层级、cast-shadow/visibility 模型、编辑 API、真实数据无真值时的评价协议。

## 本次初始化采用的决策

- v1 传感器合约锁定为 `RGB + LiDAR + calibrated cameras`；radar 作为后续决策，不阻塞 P0。
- CARLA 是重打光定量主基准；真实数据只在协议明确后报告代理指标、盲评与失败案例。
- 五类组件必须共用一个接口，不允许每条代码线用互不兼容的坐标、曝光或材质定义。
- “feed-forward”“physics-aware”“真实”均为待验证主张，只有通过对应 EXP 记录后才能写成结论。
- PPT 中的 “NeurIPS 2026” 只视为历史目标，不作为当前已确认投稿日程。
