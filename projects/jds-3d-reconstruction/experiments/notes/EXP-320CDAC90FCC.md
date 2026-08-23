---
experiment_id: "EXP-320CDAC90FCC"
status: "planned"
type: "ablation"
---

# E-alpha 循环消融：互导是否稳健优于单向引导

> 这是实验计划与证据索引，不代表实验已经执行。

## 目标

在同一批场景上对比仅表示 A、仅表示 B、单向 A→B、双向 A↔B 四种配置，检验假设 H1：是否存在互导劣于单向引导的情形。

## 当前状态

- 状态：`planned`
- 执行器：`wsl2-ubuntu2404-rtx4090`
- 加速器：`nvidia` × 1
- 类型：`ablation`

## 阻塞项

- `CODE_UNVERIFIED`：GS-Octree 代码是否可运行、能否复现论文数值尚未核实；MGSR 代码同样未核实；解除条件：取得 GS-Octree 代码并在 NeRF-Synthetic 上复现论文报告的至少一个数值
- `DATA_UNPINNED`：NeRF-Synthetic 与 OmniObject3D 尚未下载，评测协议未固定；解除条件：下载数据并登记不可变 manifest 与评测脚本

## 协议

只做四路对比，不引入任何新方法。这是论点的根基判据：若互导稳健更优，H1 为假，方向应放弃。

### 成功标准

- 四种配置在相同场景、相同迭代预算下完成训练
- 几何指标 Chamfer distance 与 F-score、渲染指标 PSNR/SSIM/LPIPS 齐全
- 至少一个场景上双向配置不优于单向配置，且差异超出种子波动

### 失败标准

- 双向配置在全部场景上稳健优于单向，且差异均超出种子波动 —— H1 为假
- 四种配置无法在相同预算下公平对比
- GS-Octree 代码无法复现原论文数值

## 代码、数据与环境

- 代码仓：待确认
- Commit：`待确认`
- 数据：0 个已登记数据入口
- OS：`linux`
- 命令：`[]`

## 可追溯关系

- Idea：IDEA-4DC79F20C0C6
- TODO：尚未关联
- 文献：尚未关联
- Claim：尚未关联

## Preflight

- 最新状态：`not-run`
- 报告：尚未生成或请查看机器记录中的 report 指针。

## 结果与解释

尚未执行，不得据此更新 Idea 或论文结论。
