"""DTU 官方评测协议的 Python 实现（accuracy / completeness / overall）。

MGSR 仓库不含评测脚本，故按 DTU 官方 Matlab 流程与其通用 Python 移植实现。
关键步骤缺一不可，少任何一步得到的数都不可与论文比较：

  1. **坐标系还原**：重建结果在 IDR 归一化帧内（已核验 COLMAP sparse 与之逐相机
     一致），而真值 stl024_total.ply 在 DTU 原始世界坐标。须左乘 scale_mat。
  2. **体素下采样到 0.2 mm**：官方协议规定的密度，直接影响两个方向的距离。
  3. **ObsMask 过滤**：只有被观测到的区域参与 accuracy，否则相机看不见的地方
     也会被计入误差。
  4. **地面平面剔除**：completeness 只统计 Plane 之上的真值点，否则桌面会主导。
  5. **max_dist=20 截断**：官方做法，抑制离群点。

自检：变换后的重建点包围盒必须与 ObsMask 的 BB 有实质重叠——
若不重叠说明坐标系搞错了，此时任何数字都是无意义的，脚本会直接报错而不是给个数。
"""
import argparse
import os

import numpy as np
import open3d as o3d
from scipy.io import loadmat
from sklearn.neighbors import KDTree


def sample_mesh_or_points(path, density):
    """网格则按面积采样，点云则直接读。返回 Nx3。"""
    if path.endswith(".ply"):
        try:
            m = o3d.io.read_triangle_mesh(path)
            if len(m.triangles) > 0:
                m.remove_unreferenced_vertices()
                area = m.get_surface_area()
                n = max(int(area / (density ** 2)), 100000)
                n = min(n, 20_000_000)
                pcd = m.sample_points_uniformly(number_of_points=n)
                return np.asarray(pcd.points), "mesh(%d 面, 采样 %d 点)" % (len(m.triangles), n)
        except Exception:
            pass
    p = o3d.io.read_point_cloud(path)
    return np.asarray(p.points), "pointcloud(%d 点)" % len(p.points)


def voxel_down(pts, size):
    p = o3d.geometry.PointCloud()
    p.points = o3d.utility.Vector3dVector(pts)
    return np.asarray(p.voxel_down_sample(size).points)


def nn_dist(query, reference):
    """query 中每点到 reference 的最近距离。"""
    return KDTree(reference, leaf_size=40).query(query, k=1)[0].ravel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recon", required=True, help="重建的 mesh 或点云 .ply")
    ap.add_argument("--scan", type=int, required=True)
    ap.add_argument("--gt_dir", required=True, help="含 stl<scan>_total.ply / ObsMask<scan>_10.mat / Plane<scan>.mat")
    ap.add_argument("--cameras", required=True, help="cameras.npz，用其 scale_mat_0 还原坐标系")
    ap.add_argument("--density", type=float, default=0.2)
    ap.add_argument("--patch", type=float, default=60.0)
    ap.add_argument("--max_dist", type=float, default=20.0)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    data, kind = sample_mesh_or_points(a.recon, a.density)
    if len(data) == 0:
        raise SystemExit("重建结果为空: " + a.recon)

    # --- 1. 归一化帧 -> DTU 世界坐标 ---
    S = np.load(a.cameras)["scale_mat_0"].astype(np.float64)
    data_w = data @ S[:3, :3].T + S[:3, 3]

    # --- 3. ObsMask ---
    om = loadmat(os.path.join(a.gt_dir, "ObsMask%d_10.mat" % a.scan))
    ObsMask, BB, Res = om["ObsMask"], om["BB"].astype(np.float64), om["Res"]
    Res = float(np.array(Res).ravel()[0])

    lo, hi = BB[0], BB[1]
    dlo, dhi = data_w.min(0), data_w.max(0)
    overlap = np.minimum(dhi, hi) - np.maximum(dlo, lo)
    frac = np.prod(np.clip(overlap, 0, None)) / max(np.prod(hi - lo), 1e-9)
    print("[自检] ObsMask BB   %s ~ %s" % (np.round(lo, 1), np.round(hi, 1)))
    print("[自检] 重建包围盒   %s ~ %s" % (np.round(dlo, 1), np.round(dhi, 1)))
    print("[自检] 体积重叠比   %.3f" % frac)
    if frac < 0.05:
        raise SystemExit("[自检失败] 变换后的重建与 ObsMask 几乎不重叠——坐标系错了，"
                         "此时任何数字都无意义。请检查 scale_mat 的应用方向。")

    # --- 2. 下采样 ---
    data_down = voxel_down(data_w, a.density)

    inb = ((data_down >= lo - a.patch) & (data_down < hi + a.patch * 2)).all(-1)
    data_in = data_down[inb]
    grid = np.around((data_in - lo) / Res).astype(np.int32)
    gin = ((grid >= 0) & (grid < np.array(ObsMask.shape)[None])).all(-1)
    grid = grid[gin]
    seen = ObsMask[grid[:, 0], grid[:, 1], grid[:, 2]].astype(bool)
    data_obs = data_in[gin][seen]

    stl = np.asarray(o3d.io.read_point_cloud(
        os.path.join(a.gt_dir, "stl%03d_total.ply" % a.scan)).points)

    # --- accuracy: 重建 -> 真值 ---
    d2s = nn_dist(data_obs, stl)
    acc = d2s[d2s < a.max_dist].mean()

    # --- 4. 地面剔除 + completeness: 真值 -> 重建 ---
    P = loadmat(os.path.join(a.gt_dir, "Plane%d.mat" % a.scan))["P"]
    above = (np.concatenate([stl, np.ones((len(stl), 1))], -1) @ P)[:, 0] > 0
    stl_above = stl[above]
    s2d = nn_dist(stl_above, data_down)
    comp = s2d[s2d < a.max_dist].mean()

    print()
    print("=" * 66)
    print("scan%d  %s  %s" % (a.scan, a.tag, kind))
    print("  重建点(下采样后) %8d   参与 accuracy 的 %8d" % (len(data_down), len(data_obs)))
    print("  真值点           %8d   平面以上 %8d" % (len(stl), len(stl_above)))
    print("-" * 66)
    print("  accuracy      (重建->真值)  %.4f mm" % acc)
    print("  completeness  (真值->重建)  %.4f mm" % comp)
    print("  overall (Chamfer)           %.4f mm" % ((acc + comp) / 2))
    print("=" * 66)


if __name__ == "__main__":
    main()
