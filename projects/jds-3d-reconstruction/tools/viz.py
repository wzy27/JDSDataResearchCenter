"""E-zeta 的可视化。目标不是好看，是**检验机制**。

四张图，每张回答一个具体问题：

  1. 误差分布      —— 5.4% 的劣化是整体抬升，还是尾部变重？
  2. 误差 vs 深度  —— **关键**。若劣化集中在远处，直接支持 max 归一化的嫌疑
                      （max 由远处离群深度主导，两侧各自归一化即错位）
  3. 空间分布      —— 劣化落在物体的哪些部位
  4. 训练动力学    —— GEAR 式的三条损失曲线，看环路是收敛还是震荡

坐标系：重建在 IDR 归一化帧，真值在 DTU 世界坐标，须左乘 scale_mat（与 dtu_eval.py 一致）。
"""
import os
import numpy as np
import open3d as o3d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import gridspec
from sklearn.neighbors import KDTree

ROOT = os.path.expanduser("~/fastrelight/mutual/out/ezeta")
BASE = os.path.expanduser("~/fastrelight/mutual/out/dtu_scan24")
GT = os.path.expanduser("~/fastrelight/data/dtu_gt")
CAM = os.path.expanduser("~/fastrelight/data/dtu2dgs/2DGS_data/DTU/scan24/cameras.npz")
OUT = os.path.expanduser("~/fastrelight/analysis/figs")
os.makedirs(OUT, exist_ok=True)

C_LO = "#2D4A7C"      # w=0.01 原值
C_HI = "#A8442A"      # w=0.5  加强 50 倍
C_MID = "#1F6F5C"     # w=0.05 内部最优
INK = "#16202B"
MUTED = "#6B7785"
RULE = "#DCE1E7"

# WSL 下 matplotlib 自带字体无 CJK，中文标签会渲染成方框。
# 从 Windows 侧取 DengXian（已 cp 到 ~/.local/share/fonts/）。
from matplotlib import font_manager as fm
_ft = os.path.expanduser("~/.local/share/fonts/Deng.ttf")
if os.path.exists(_ft):
    fm.fontManager.addfont(_ft)
    _fn = fm.FontProperties(fname=_ft).get_name()
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [_fn, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": RULE, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.color": RULE, "grid.linewidth": .6, "grid.alpha": .8,
})

cams = np.load(CAM)
S = cams["scale_mat_0"].astype(np.float64)


def load_world(path):
    p = np.asarray(o3d.io.read_point_cloud(path).points)
    return p @ S[:3, :3].T + S[:3, 3]


def cam_centers():
    import cv2
    C = []
    i = 0
    while f"world_mat_{i}" in cams:
        P = (cams[f"world_mat_{i}"] @ cams[f"scale_mat_{i}"])[:3, :4]
        t = cv2.decomposeProjectionMatrix(P)[2]
        c = (t[:3] / t[3]).ravel()
        C.append(c @ S[:3, :3].T + S[:3, 3])
        i += 1
    return np.array(C)


print("加载真值…", flush=True)
stl = np.asarray(o3d.io.read_point_cloud(os.path.join(GT, "stl024_total.ply")).points)
tree_gt = KDTree(stl, leaf_size=40)
Cc = cam_centers()
print(f"  真值 {len(stl)} 点，相机 {len(Cc)} 个", flush=True)


def err_of(path, sub=400000):
    pts = load_world(path)
    if len(pts) > sub:
        idx = np.random.RandomState(0).choice(len(pts), sub, replace=False)
        pts = pts[idx]
    d = tree_gt.query(pts, k=1)[0].ravel()
    keep = d < 20.0                       # 与官方协议一致的截断
    return pts[keep], d[keep]


RUNS = {
    "w=0.01（MGSR 原值）": (f"{BASE}/total/point_cloud/iteration_20000_ref/point_cloud.ply", C_LO),
    "w=0.05（内部最优）":  (f"{ROOT}/w005/total/point_cloud/iteration_20000_ref/point_cloud.ply", C_MID),
    "w=0.5（加强 50×）":   (f"{ROOT}/w05/total/point_cloud/iteration_20000_ref/point_cloud.ply", C_HI),
}
data = {}
for k, (p, c) in RUNS.items():
    if not os.path.exists(p):
        print("  缺:", p); continue
    pts, d = err_of(p)
    data[k] = (pts, d, c)
    print(f"  {k}: {len(pts)} 点，中位误差 {np.median(d):.3f} mm，均值 {d.mean():.3f}", flush=True)

# 每点到相机组的中位深度，作为「远近」的代理
def median_depth(pts):
    step = max(1, len(pts) // 60000)
    q = pts[::step]
    D = np.linalg.norm(q[:, None, :] - Cc[None, :, :], axis=-1)
    md = np.median(D, axis=1)
    return q, md


# ============ 图 1+2：误差分布 与 误差 vs 深度 ============
fig = plt.figure(figsize=(11, 4.2))
gs = gridspec.GridSpec(1, 2, width_ratios=[1, 1.15], wspace=.26)

ax = fig.add_subplot(gs[0])
for k, (pts, d, c) in data.items():
    ax.hist(d, bins=np.linspace(0, 6, 121), histtype="step", lw=1.7,
            color=c, label=k, density=True)
ax.set_xlabel("每点到真值的距离 (mm)")
ax.set_ylabel("密度")
ax.set_title("误差分布：劣化来自尾部还是整体？", fontsize=10, loc="left", pad=10)
ax.legend(frameon=False, fontsize=8.5)

ax2 = fig.add_subplot(gs[1])
for k, (pts, d, c) in data.items():
    q, md = median_depth(pts)
    dq = d[::max(1, len(pts) // 60000)][:len(q)]
    bins = np.quantile(md, np.linspace(0, 1, 13))
    bins = np.unique(bins)
    cen, mid, lo, hi = [], [], [], []
    for i in range(len(bins) - 1):
        m = (md >= bins[i]) & (md < bins[i + 1])
        if m.sum() < 50:
            continue
        cen.append(.5 * (bins[i] + bins[i + 1]))
        v = dq[m]
        mid.append(np.median(v)); lo.append(np.quantile(v, .25)); hi.append(np.quantile(v, .75))
    ax2.plot(cen, mid, color=c, lw=1.9, label=k)
    ax2.fill_between(cen, lo, hi, color=c, alpha=.13, lw=0)
ax2.set_xlabel("到相机组的中位距离 (mm)  →  越右越远")
ax2.set_ylabel("到真值的距离中位数 (mm)")
ax2.set_title("误差 vs 深度：劣化是否集中在远处？（阴影为四分位区间）",
              fontsize=10, loc="left", pad=10)
ax2.legend(frameon=False, fontsize=8.5)
fig.savefig(f"{OUT}/fig_err_and_depth.png", dpi=170, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("-> fig_err_and_depth.png", flush=True)


# ============ 图 3：空间误差分布，两权重并排 + 差异 ============
def project(pts):
    """主成分投影到最展开的两个方向，保证两幅图同一坐标系。"""
    return pts[:, [0, 2]], pts[:, 1]


keys = [k for k in ["w=0.01（MGSR 原值）", "w=0.5（加强 50×）"] if k in data]
if len(keys) == 2:
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))
    vmax = 2.5
    for ax, k in zip(axes[:2], keys):
        pts, d, c = data[k]
        xy, _ = project(pts)
        s = ax.scatter(xy[:, 0], xy[:, 1], c=np.clip(d, 0, vmax), s=.4,
                       cmap="inferno_r", vmin=0, vmax=vmax, linewidths=0, rasterized=True)
        ax.set_title(k, fontsize=10, loc="left", pad=8)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    cb = fig.colorbar(s, ax=axes[:2], fraction=.026, pad=.012)
    cb.set_label("到真值的距离 (mm)", fontsize=8.5)
    cb.outline.set_edgecolor(RULE)

    # 差异图：同一空间网格内的误差中位数之差
    a_pts, a_d, _ = data[keys[0]]
    b_pts, b_d, _ = data[keys[1]]
    axy, _ = project(a_pts); bxy, _ = project(b_pts)
    lo = np.minimum(axy.min(0), bxy.min(0)); hi = np.maximum(axy.max(0), bxy.max(0))
    NB = 90
    ex = np.linspace(lo[0], hi[0], NB + 1); ey = np.linspace(lo[1], hi[1], NB + 1)

    def grid_med(xy, d):
        ix = np.clip(np.digitize(xy[:, 0], ex) - 1, 0, NB - 1)
        iy = np.clip(np.digitize(xy[:, 1], ey) - 1, 0, NB - 1)
        G = np.full((NB, NB), np.nan)
        key = ix * NB + iy
        order = np.argsort(key)
        k_s, d_s = key[order], d[order]
        edges = np.searchsorted(k_s, np.arange(NB * NB + 1))
        for cell in range(NB * NB):
            a, b = edges[cell], edges[cell + 1]
            if b - a >= 8:
                G[cell // NB, cell % NB] = np.median(d_s[a:b])
        return G

    GA, GB = grid_med(axy, a_d), grid_med(bxy, b_d)
    D = GB - GA
    m = np.nanpercentile(np.abs(D), 96)
    im = axes[2].imshow(D.T, origin="lower", cmap="RdBu_r", vmin=-m, vmax=m,
                        extent=[ex[0], ex[-1], ey[0], ey[-1]], aspect="equal",
                        interpolation="nearest")
    axes[2].set_title("差异：w=0.5 减 w=0.01（红=变差）", fontsize=10, loc="left", pad=8)
    axes[2].set_xticks([]); axes[2].set_yticks([]); axes[2].grid(False)
    cb2 = fig.colorbar(im, ax=axes[2], fraction=.046, pad=.012)
    cb2.set_label("误差之差 (mm)", fontsize=8.5)
    cb2.outline.set_edgecolor(RULE)
    fig.savefig(f"{OUT}/fig_spatial.png", dpi=165, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("-> fig_spatial.png", flush=True)
    frac_worse = np.nanmean(D > 0)
    print(f"   变差的网格占比 {100*frac_worse:.1f}%", flush=True)


# ============ 图 4：训练动力学 ============
TR = {
    "w=0.001": (f"{ROOT}/w0001/total/ezeta_trace.tsv", "#8894A3"),
    # 2026-08-24 那次基线运行早于轨迹记录的加入，故无 trace；
    # 改用 seed=1 的 w=0.01 重复跑，权重相同、仅种子不同。
    "w=0.01（原值）": (f"{ROOT}/s1_w001/total/ezeta_trace.tsv", C_LO),
    "w=0.05": (f"{ROOT}/w005/total/ezeta_trace.tsv", C_MID),
    "w=0.5": (f"{ROOT}/w05/total/ezeta_trace.tsv", C_HI),
}
fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.5))
titles = [("loss_ref", 1, "外观支自身损失"), ("depth_loss", 2, "耦合项（geo→ref）"),
          ("loss_n", 3, "几何支自身损失")]


def smooth(v, k=15):
    if len(v) < k:
        return v
    return np.convolve(v, np.ones(k) / k, mode="valid")


for ax, (nm, col, tt) in zip(axes, titles):
    for k, (p, c) in TR.items():
        if not os.path.exists(p):
            continue
        rows = [l.split("\t") for l in open(p) if not l.startswith("#") and l.strip()]
        it = np.array([int(r[0]) for r in rows])
        v = np.array([float(r[col]) for r in rows])
        sv = smooth(v)
        ax.plot(it[:len(sv)], sv, color=c, lw=1.5, label=k)
    ax.set_yscale("log")
    ax.set_xlabel("互导迭代")
    ax.set_title(tt, fontsize=10, loc="left", pad=8)
axes[0].set_ylabel("损失（15 点滑动平均，对数轴）")
axes[2].legend(frameon=False, fontsize=8, loc="upper right")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_dynamics.png", dpi=170, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("-> fig_dynamics.png", flush=True)

print("\n全部图输出到", OUT)
