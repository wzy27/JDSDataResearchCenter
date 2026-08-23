# 分析与预处理脚本

这些脚本产出仓库中 `artifacts/` 下的证据，因此纳入 Git 以保证结果可复现。大文件、数据集、权重和训练输出仍不进入 Git。

跨机同步只需 clone 本仓库；执行器侧的路径通过环境变量覆盖，脚本内无硬编码绝对路径。

## 环境构建

```bash
FASTRELIGHT_ROOT=$HOME/fastrelight CONDA_ROOT=$HOME/miniforge3 bash setup_deps.sh
FASTRELIGHT_ROOT=$HOME/fastrelight CONDA_ROOT=$HOME/miniforge3 bash setup_ext.sh
```

上游锁定环境与本机实际环境的三处偏离，见 [`../sources/2026-08-23_executor_environment_build.md`](../sources/2026-08-23_executor_environment_build.md)。

## 数据准备

`extract_masks_hf.py` —— 生成 sky mask 与 fine dynamic mask。替代上游 `datasets/tools/extract_masks.py`（后者依赖 `mmcv-full==1.2.7` + `cu111`，不支持 sm_89，在 RTX 4090 上无法运行）。使用同一权重的 HuggingFace 版本，输出格式与上游逐项对齐。

```bash
python extract_masks_hf.py \
  --data-root $FASTRELIGHT_ROOT/drivestudio/data/nuscenes/processed_10Hz/mini \
  --scenes 000,001,008 --process-dynamic-mask \
  --duty 0.6 --mem-fraction 0.6 --batch 1 --skip-existing
```

GPU 占用受 `gpu-budget` skill 约束，详见 [`../../../.claude/skills/gpu-budget/SKILL.md`](../../../.claude/skills/gpu-budget/SKILL.md)。`--batch` 需保证每轮 GPU 工作量在 50–500 ms，否则休眠会被 `max_sleep` 截断而使实际占空比高于目标；检查输出中的 `clamped_iterations`。

## 观测条件审计与分层

按依赖顺序运行：

```bash
# 1. 距离、投影像素高度、观测次数
python observation_sufficiency.py --root <processed>/mini --out ped_observation_stats.json

# 2. 像素级可见比（凸包光栅化 + 深度排序）
python pixel_visibility.py --root <processed>/mini --out ped_pixel_visibility.json --scale 0.5

# 3. 二维分层分配
python strata.py --obs-stats ped_observation_stats.json \
                 --vis-stats ped_pixel_visibility.json --out ped_strata.json
```

前两步只读标注与标定，不需要 GPU。结论见 [`../sources/2026-08-23_nuscenes_mini_observation_audit.md`](../sources/2026-08-23_nuscenes_mini_observation_audit.md) 与 [`../sources/2026-08-23_strata_definition_and_evaluator.md`](../sources/2026-08-23_strata_definition_and_evaluator.md)。

## 分层评测

`stratified_eval.py` —— 按 (有效像素分辨率 × 可见比) 分层报告 human-region 的 PSNR/SSIM。与 DriveStudio 内置 `human_psnr` 的区别：内置指标把一帧内所有行人像素合并为单一 mask，远处小目标被近处大目标淹没。

```bash
python stratified_eval.py \
  --scene-dir <processed>/mini/000 --pred-dir <render_output> \
  --strata ped_strata.json --scene-key 000 \
  --frame-ids range:0:200:10 --out stratified_metrics.json
```

预测图为 DriveStudio 在 `save_images=True` 下导出的逐帧 PNG，命名 `{test_idx:03d}_{cam_idx:03d}.png`。

**注意 `--frame-ids` 的语义**：其取值须为**原始帧号**（用于定位真值与标定），而 `--pred-dir` 中的文件按**测试集索引**编号。两者的对应关系尚未在真实渲染输出上核对过，首次使用时必须验证。

### 已验证的性质

以真值加已知噪声伪造预测，在 CPU 上验证：

- 噪声单调性：σ = 0.005 / 0.02 / 0.08 → 45.19 / 33.90 / 22.01 dB（σ=0.02 理论值 33.98 dB）。
- 分层分辨能力：仅向 `px<96` 层实例注入额外噪声 → 该层降 12.15 dB，其余层 −0.02 dB，分离比约 807 倍。

自测使用合成噪声，**不构成对真实渲染结果的验证**。
