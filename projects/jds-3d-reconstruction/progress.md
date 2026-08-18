# 项目进度审计（2026-08-18）

状态定义：

- `已验证`：存在可复现代码、配置、数据版本、指标和产物。
- `原型`：存在代码或产物，但依赖硬编码、缺少完整复现链或仍有已知问题。
- `有线索`：只看到文档、数据或视频，不能证明实现完成。
- `未见证据`：当前 S3 材料不足以证明已开始。

## 总览

| 工作线 | 状态 | 已有证据 | 主要缺口 |
|---|---|---|---|
| 人体/行人重建 | 原型，局部已验证 | LHM 源码快照、Forwardrobe、SMPL/LHM 注入补丁、10k-step StageA 指标、行人轨迹与评测视频 | 工程硬编码；服装/LBS 仍有形变冲突；代码版本与补丁顺序未固化 |
| 车辆重建 | 未见证据 | OmniRe 官方基线本身支持刚性车辆 | S3 中没有车辆模块代码、训练配置、checkpoint、独立渲染或指标 |
| 静态场景重建 | 有线索 | 多个 `Background` 40k-step 视频；PPT 涉及 CARLA、DriveStudio、NuScenes | 缺代码 commit、数据 scene ID、配置、日志、checkpoint 和定量质量评估 |
| 重打光 | 数据准备/概念原型 | 40 组训练与 10 组测试光照小数组；代码中有 relighting runtime switch 注释 | 没有材质/光照分解、阴影/可见性模型、训练记录或物理一致性评测 |
| 可编辑统一合成 | 原型 | 自定义 LHM Avatar 注入与指定行人替换；背景/行人组合视频 | 行人 ID 和路径硬编码；没有车辆编辑；没有统一坐标/光照接口；旋转仍有 TODO |

## 人体/行人重建

### 已完成或基本完成

- 获取并保存 LHM 官方实现快照及其 SMPL-X、姿态估计等依赖。
- 建立 NeuMan → LHM Avatar → Gaussian 适配 → 全身动态优化的 Forwardrobe V100 基线结构。
- 建立把自定义 LHM Gaussian Avatar 注入 SMPLNodes、过滤原始行人的代码原型。
- Patch10 StageA 从头训练完成 10,000/10,000 steps，存在最终 checkpoint 清单和验证表。
- 该实验最终 dynamic PSNR 为 24.1217，对应 LHM base 为 20.2916；最终 dynamic LPIPS 为 0.0769，base 为 0.0838。
- cloth alpha IoU 的窗口均值由 0.8228 提升到 0.8832，outside-occ-aware 泄漏由 0.005512 降至 0.001937。

### 仍有问题

- 当前 SMPLNodes 片段固定 `render_smpl_instance_ids = 17`，并引用机器绝对路径，不是通用接口。
- 自定义 Avatar 的 Gaussian 旋转传播仍标记为 TODO。
- Forwardrobe 基线明确关闭了 clothing segmentation、garment/body split、albedo×shading decomposition 和 DynaAvatar diffused skinning field。
- seam-close/stretch 写回 Gaussian 中心对大动作可减少裙摆分裂，但对 GT/小动作会造成内缩；需要动作相关强度而不是固定开关。
- StageA 指标只覆盖单个 subject/有限验证帧，尚不能代表多行人、多服装和自动驾驶远近尺度。

## 车辆重建

OmniRe 官方方案以局部 canonical space 中的静态 Gaussian 表示车辆，并通过刚体变换产生运动。但当前 S3 归档没有发现 `omnire`、`drivestudio` 或 vehicle 模块代码，也没有车辆独立 checkpoint、渲染分层和指标。因此不能把车辆重建标为已完成。

## 静态场景重建

归档包含 `full_set_40000_Background_*` 等视频，说明至少运行过背景渲染或训练结果导出。但这些视频没有配套 scene ID、代码 commit、配置、日志和 checkpoint。当前只能标记为“有产物线索”，不能复现或比较几何/外观质量。

## 重打光

`light_data.zip` 包含 40 个训练与 10 个测试 `.npy` 光照条目；另一个 SMPLNodes 片段只出现“relighting training runtime switch”，实际颜色仍直接使用 SH/RGB。Forwardrobe 文档明确说 separate albedo × shading heads 尚未启用。因此重打光尚未形成可用模块。

最低完成标准应包括：材质/反照率表示、环境光或光源表示、可见性/阴影、跨实体统一曝光与色调、训练/测试光照分离，以及 relight 后的定量和人工评测。

## 可编辑统一合成

已有“隐藏原 SMPL 行人并拼接自定义 Avatar Gaussians”的原型，说明替换人物的方向可行。但尚未看到车辆替换、任意 actor 选择、统一坐标尺度、碰撞/接触、遮挡、阴影传递和跨实体重打光。因此距离最终“可编辑且光照真实”的目标仍有明显系统集成缺口。

## 当前结论

最值得保留的成果是人体 StageA 训练和 LHM 注入链；最优先的工程工作不是继续增加零散补丁，而是先恢复一个可复现的 OmniRe/DriveStudio 基线仓库，然后把人体原型作为独立 actor representation 接入。车辆和场景应先分别建立可审计基线，重打光应在三类几何表示稳定后以统一接口实现。
