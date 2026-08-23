# 双表示互导优化的成立条件：立论与证伪设计

> 对应 `IDEA-4DC79F20C0C6`。本文先给出论点与支撑证据，再设计**能够推翻该论点的实验**，最后才谈方法。
> 顺序如此安排，是因为此前七个候选方向连续被证伪，其中多次源于先设计方法、后才发现问题不成立。

## 1. 论点

> **SDF ↔ 3D Gaussians、2DGS ↔ 3DGS 等双表示互导优化已被多篇工作采用并取得效果，但无人研究该循环的成立条件——何时收敛、何时把一方的误差放大后喂给另一方、warm-up 与切换时机依据什么确定。**

## 2. 支撑证据

### 2.1 语料检索

在 1239 篇会议全文（ICCV 2025 + CVPR 2026 部分）中，限定 3DGS / 隐式表示上下文：

| 子表述 | 主题级论文数 |
|---|---:|
| 互导 / 相互监督 | 2 |
| 交替优化 | 4 |
| 双表示混合 | 9 |
| **收敛性 / 稳定性分析** | **0** |
| 初始化敏感 / 坏极小值 | 1 |

**同时讨论「互导或交替优化」与「收敛或稳定性」的论文：0 篇。**

强信号仅命中 MGSR 自身。即：该模式在被使用，但未被检视。

### 2.2 两篇采用该模式的工作均未分析它

**GS-Octree**（arXiv:2406.18199）结论原文：

> "The method confirms the possibility that Gaussians can guide geometric optimization, and **good geometry** can further optimize Gaussian points."

「good」一词承担了全部重量。若几何本身有误，循环是自我纠正还是互相强化，论文未回答。该文亦无 Limitations 段。

**MGSR**（ICCV 2025）原文：

> "Prior to alternating optimization, the two modules undergo an **independent warm-up stage**, and an **auto-stop strategy** is introduced to reduce unnecessary computational burdens."
> "To the best of our knowledge, MGSR is the **first** GS-based approach that investigates the simultaneous enhancement of rendering and reconstruction, as well as the **first mutual-boosted work** on GS involving both 2DGS and 3DGS."

作者自述为首次，说明该线刚开启，尚无回头检视。warm-up 时长、切换时机、auto-stop 判据均无原理依据。

### 2.3 三个手工旋钮已定位

| 旋钮 | 出处 | 当前依据 |
|---|---|---|
| 八叉树细分层级 | GS-Octree | 正文仅述「according to the data contained in each node」与「progressive refinement guided by the SDF」，Figure 3 展示 level 6–9 的效果，**层级为手工指定的超参**，未给出细分准则 |
| warm-up 时长 / 切换频率 / auto-stop | MGSR | 无原理，工程选择 |
| singular-Hessian 与 Eikonal 的权重 | Wang et al., SIGGRAPH Asia 2023，被 GS-Octree 借用 | **代码审计修正**：实现中并无退火，而是硬编码常数 `scale_hess=1e-12`、`scale_eiko=1e-6`（相差六个数量级），另有 `eikon_thres_min=0.8`、`eikon_thres_max=1.5`、`gaussian_sigma=0.1`、`max_n_samples=64`。见 `2026-08-24_mgsr_code_audit.md` |

### 2.4 借用项的适用边界与原猜测不符

singular-Hessian 的原理是：SDF 的 Hessian 在表面附近的薄壳空间内奇异（微分几何结论），故强制近表面点 Hessian 行列式为零。

**原作者自述的局限是 LiDAR 类输入**——条纹分布、稀疏、大量缺失；他们反而声称在尖锐边（octa-flower）上优于 Hessian energy 与 DiGS。

因此「尖锐/薄结构失效」这一先前猜测**不成立**。真实边界在**点分布不规则、稀疏、缺失**时——而这恰是 GS-Octree 场景中的典型形态：强光下高光区域的 Gaussian 分布本就不规则。

## 3. 可证伪的假设

| # | 假设 | 若为假则 |
|---|---|---|
| **H1** | 存在可构造的初始条件或场景，使互导优化的结果**劣于**单向引导或单一表示 | 不存在失效区域，无问题可研究 |
| **H2** | 三个旋钮的取值对最终几何精度的影响**显著超出随机种子波动** | 当前启发式取值已足够，无改进空间 |
| **H3** | 循环的成败在优化**早期**即可由某个可测信号预示 | 无法预测则只能事后判断，方法价值大减 |

三条中 **H1 是根基**：若 H1 为假，整个论点崩塌，应立即放弃。

## 4. 证伪实验设计

原则：**每个实验的设计目标是推翻对应假设，而非确认它。** 先跑最可能推翻 H1 的实验。

### E-α 循环消融（检验 H1，最高优先级）

- **做什么**：同一批场景上跑四种配置——仅表示 A（八叉树 SDF）、仅表示 B（3DGS）、单向 A→B、双向 A↔B。
- **得到**：几何精度（Chamfer / F-score）与渲染质量（PSNR/SSIM/LPIPS）的四路对比。
- **推翻条件**：若 A↔B 在所有场景上稳健优于 A→B，则 H1 为假。
- **数据**：NeRF-Synthetic、OmniObject3D（GS-Octree 原用数据），单卡可跑。

### E-β 受控误差注入（检验 H1 的机制，核心实验）

- **做什么**：取已收敛的良好 SDF，注入**可控幅度与类型**的扰动（低频形变、局部凹陷、高频噪声、拓扑错误），再运行互导循环，测量扰动随迭代是**收缩还是增长**。
- **得到**：扰动幅度 → 迭代次数的演化曲线，按扰动类型分层。
- **为何是核心**：它直接测量「误差被纠正还是被放大」，且不依赖场景差异这一混杂因素。
- **推翻条件**：若所有扰动类型均单调收缩，H1 为假。

### E-γ 旋钮敏感性（检验 H2）

- **做什么**：扫描三个旋钮（细分层级、warm-up 时长与切换频率、Hessian 退火曲线），同时以 3 个随机种子建立波动基线。
- **得到**：各旋钮的效应量与种子波动的比值。
- **推翻条件**：效应量与种子波动同量级则 H2 为假。

### E-δ 早期可预测性（检验 H3，仅在 H1 成立后进行）

- **做什么**：从 E-α/E-β 的训练轨迹中，寻找在早期迭代即与最终成败相关的可测量（两表示间的一致性残差、SDF 梯度范数分布、Gaussian 离面比例等）。
- **推翻条件**：无任何早期量与最终结果相关。

## 5. 止损点

- **E-α 与 E-β 均未推翻 H1 之前，不进入方法设计。**
- 若 E-α 显示互导稳健更优且 E-β 显示扰动单调收缩 → **论点不成立，放弃该方向**，不再寻找第四个实验来挽救。
- 若 E-γ 显示旋钮效应量与种子波动同量级 → 论点降级为「循环稳健但缺乏理论说明」，价值大减，需重新评估是否值得继续。

## 6. 预注册

在见到结果前固定：

- 几何指标为 Chamfer distance 与 F-score（阈值随数据集惯例），渲染指标为 PSNR/SSIM/LPIPS。
- 探索阶段每配置 1 个随机种子；进入结论的对比一律 3 个种子并报告置信区间。
- H2 的判据为：旋钮效应量的 95% 置信区间与种子波动的 95% 置信区间不重叠。
- 所有训练须经 `gpu-budget` 约束并报告实测占空比。

## 7. 尚未完成的证伪

- **通道 B 引文图谱未走**：需在 Semantic Scholar 上查 GS-Octree、MGSR 与 Neural-Singular-Hessian 的前向引用，确认无人已做该分析。**该项须由研究者执行。**
- 语料仅覆盖 ICCV 2025 与部分 CVPR 2026（1239 篇，仍在增长），未覆盖 SIGGRAPH、TOG、TVCG 等图形学场馆——而双表示混合与几何正则的工作常发表于此，**这是当前最大的检索盲区**。
- 未核实 GS-Octree 与 MGSR 的代码可运行性。

## 8. 与既往工作的关系

本方向不否定 GS-Octree 与 MGSR，而是检视二者共享的基础模式。若结论为「循环在多数条件下稳健」，则是对该模式的正面支持；若发现失效区域，则给出使用条件。两种结果都有价值，但只有后者足以支撑一篇方法论文——**这一点必须在投入前认清，不得在结果出来后重新定义成功标准。**
