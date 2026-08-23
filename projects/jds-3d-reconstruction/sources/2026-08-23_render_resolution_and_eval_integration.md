# 2026-08-23 训练渲染分辨率与评测对接

> 数据集加载冒烟测试（scene 000，6 相机，CPU 预载）的结论。该测试同时解决了分层评测器与 DriveStudio 渲染输出的对接问题。

## 1. 数据集加载通过

| 项 | 值 |
|---|---|
| 时间步 | 191 |
| 相机 | 6（CAM_FRONT / FRONT_LEFT / FRONT_RIGHT / BACK_LEFT / BACK_RIGHT / BACK） |
| 训练图像 | 1032 |
| 测试图像 | 114（`test_image_stride=10`） |
| sky / human / dynamic mask | 均加载成功 |
| SMPL | 加载成功 |
| LiDAR | 191 帧，已投影到 6 个相机 |

## 2. 训练与渲染的实际分辨率

`configs/datasets/nuscenes/6cams.yaml` 的 `downscale_when_loading = [3,3,3,3,3,3]`，因此**训练与渲染在 533×300 下进行**，而非原生 1600×900。这是上游对 nuScenes 6 相机的默认设置，保留它才能与已发表数值可比。

这项设置显著改变了对研究前提的表述。行人投影高度换算：

| | 原生 1600×900 | 训练渲染 533×300 |
|---|---:|---:|
| 最佳视角 p10 | 76.9 px | **25.6 px** |
| 最佳视角 p50 | 163.8 px | 54.6 px |
| 典型视角 p10 | 48.5 px | **16.2 px** |
| 典型视角 p50 | 85.0 px | **28.3 px** |

训练分辨率下的占比：

| 阈值 | 行人数 | 占比 |
|---|---:|---:|
| 最佳视角 < 16 px | 5 / 227 | 2.2% |
| 最佳视角 < 24 px | 20 / 227 | 8.8% |
| **最佳视角 < 32 px** | **46 / 227** | **20.3%** |
| 最佳视角 < 48 px | 102 / 227 | 44.9% |

**在实际训练分辨率下，行人的典型视角只有 28 px 高；20.3% 的行人在任何视角下都不超过 32 px。**

这是先前「有效像素分辨率不足」表述的更准确版本。分层阈值的换算：`96 / 160 / 320` px（原生）对应 `32 / 53 / 107` px（渲染）。分层定义仍以原生几何为准（物理量与分辨率设置无关），但报告时应同时给出渲染分辨率下的数值。

## 3. 评测器对接已核对

先前记为「未在真实渲染输出上核对」的帧号映射，现已通过读取上游代码与数据集对象确认：

- 测试集为 19 个时间步 × 6 相机 = 114 张，时间步为 `[10, 20, ..., 190]`；
- `save_concatenated_videos` 中外层 `i` 遍历时间步（`num_timestamps`），内层按 `[i*num_cams : (i+1)*num_cams]` 切出该时间步的各相机；
- `save_images=True` 时导出为 `{i:03d}_{j:03d}.png`，`i` 为**时间步序号**（0..18），`j` 为**相机序号**（0..5）；
- 每个 render key（`rgbs`、`gt_rgbs`、`depths` 等）各有独立目录，`--pred-dir` 应指向 `rgbs` 的目录。

因此 `stratified_eval.py` 的正确调用为：

```bash
python stratified_eval.py --scene-dir <processed>/mini/000 \
  --pred-dir <output>/.../rgbs --strata ped_strata.json --scene-key 000 \
  --frame-ids range:10:200:10 --cam-ids 0,1,2,3,4,5 \
  --width 533 --height 300 --native-width 1600 --native-height 900 \
  --out stratified_metrics.json
```

`--frame-ids range:10:200:10` 恰为 19 个时间步，与导出的 `i` 序号一一对应。

**仍未核对的部分**：上述结论来自代码阅读与数据集对象，尚未在一次真实渲染输出上验证。首次训练产出图像后必须核对文件数（19×6=114）与内容，再采信分层数值。

## 4. 对分层评测的影响

评测在 533×300 上进行，而真值 human mask 与 3D box 凸包按原生分辨率生成。`stratified_eval.py` 已支持 `--native-width/--native-height` 并据此缩放内参；该缩放逻辑的缺失曾导致评分实例数为 0，见 [`2026-08-23_strata_definition_and_evaluator.md`](2026-08-23_strata_definition_and_evaluator.md)。

在 533×300 下，`px<96`（原生）层的行人只有约 32 px 高，其像素样本量很小。评测器已设 `max(4, int(16*sx*sy))` 的最小像素阈值；该阈值在此分辨率下为 4 像素，需在首次真实评测后复核是否过松。
