"""把行人实例分配到 (有效像素分辨率 x 可见比) 二维分层。

两条轴由 2026-08-23 的观测审计确定：
  - 有效像素分辨率：最佳视角投影高度，来自 observation_sufficiency.py
  - 可见比：面积加权像素级可见比，来自 pixel_visibility.py
二者 Spearman 秩相关 0.199，近似独立，故用二维网格而非一维。
"""
import argparse, json
import numpy as np

PX_BINS = [0, 96, 160, 320, float("inf")]
PX_LABELS = ["px<96", "px96-160", "px160-320", "px>320"]
VIS_BINS = [0.0, 0.5, 0.8, 1.01]
VIS_LABELS = ["vis<0.5", "vis0.5-0.8", "vis>0.8"]


def bin_of(value, bins, labels):
    for i in range(len(labels)):
        if bins[i] <= value < bins[i + 1]:
            return labels[i]
    return labels[-1]


def build(obs_stats_path, vis_stats_path):
    A = json.load(open(obs_stats_path))
    B = json.load(open(vis_stats_path))
    out = {}
    for scene, arr in A.items():
        vis = {x["instance_id"]: x for x in B.get(scene, [])}
        rows = {}
        for a in arr:
            if a.get("n_observations", 0) == 0:
                continue
            v = vis.get(a["instance_id"])
            if not v or v.get("n_observations", 0) == 0:
                continue
            px = a["px_height_max"]
            vf = v["visible_fraction_area_weighted"]
            rows[a["instance_id"]] = {
                "class_name": a["class_name"],
                "px_height_max": px,
                "px_height_median": a["px_height_median"],
                "depth_median": a["depth_median"],
                "visible_fraction_area_weighted": vf,
                "independent_observations": round(a["n_frames"] / 5.0, 1),
                "px_stratum": bin_of(px, PX_BINS, PX_LABELS),
                "vis_stratum": bin_of(vf, VIS_BINS, VIS_LABELS),
                "cell": f"{bin_of(px, PX_BINS, PX_LABELS)}|{bin_of(vf, VIS_BINS, VIS_LABELS)}",
            }
        out[scene] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs-stats", required=True)
    ap.add_argument("--vis-stats", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    s = build(a.obs_stats, a.vis_stats)
    json.dump(s, open(a.out, "w"), indent=2)
    cells = {}
    for scene in s.values():
        for r in scene.values():
            cells[r["cell"]] = cells.get(r["cell"], 0) + 1
    print(f"instances assigned: {sum(len(v) for v in s.values())}")
    for c in sorted(cells):
        print(f"  {c:24s} {cells[c]:4d}")
    print("written", a.out)


if __name__ == "__main__":
    main()
