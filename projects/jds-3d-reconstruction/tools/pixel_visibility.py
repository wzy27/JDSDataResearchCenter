"""像素级行人可见性：凸包光栅化 + 画家算法深度排序。

替代先前的 2D 包围盒遮挡代理。对每个 (frame, camera)：
  1. 将所有标注 3D box 的 8 角点投影，取凸包作为轮廓；
  2. 按最近角点深度由远及近绘制到 id-buffer（画家算法）；
  3. 行人的可见像素数 / 其单独绘制时的像素数 = 可见比。

只读标注与标定，不训练、不渲染场景、不使用 GPU。
局限：只统计被"已标注物体"造成的遮挡，不含建筑、杆件、未标注静物。
"""
import argparse, json, os
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw

PED_PREFIX = ("human.pedestrian",)


def load_mat(p): return np.loadtxt(p).reshape(4, 4)


def load_K(p):
    v = np.loadtxt(p)
    return np.array([[v[0], 0, v[2]], [0, v[1], v[3]], [0, 0, 1]]), v[1]


def corners_world(o2w, size):
    w, l, h = size
    pts = np.array([[x, y, z, 1.0]
                    for x in (-l / 2, l / 2) for y in (-w / 2, w / 2) for z in (-h / 2, h / 2)]).T
    return (np.asarray(o2w) @ pts)[:3].T


def project_hull(corners, w2c, K, W, H, scale):
    """返回 (图像坐标凸包多边形, 最近角点深度, 落在画幅内的角点比例)。"""
    pts = np.hstack([corners, np.ones((len(corners), 1))])
    cam = (w2c @ pts.T).T[:, :3]
    front = cam[:, 2] > 0.1
    if front.sum() < 3:
        return None, np.inf, 0.0
    c = cam[front]
    uv = (K @ c.T).T
    uv = uv[:, :2] / uv[:, 2:3]
    inside = ((uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H))
    if not inside.any():
        return None, float(c[:, 2].min()), 0.0
    uv = uv * scale
    try:
        from scipy.spatial import ConvexHull
        hull = uv[ConvexHull(uv).vertices]
    except Exception:
        hull = uv
    return [tuple(p) for p in hull], float(c[:, 2].min()), float(inside.mean())


def analyse_scene(scene_dir, n_cams, W, H, scale):
    info = json.load(open(os.path.join(scene_dir, "instances", "instances_info.json")))
    Ks = {}
    for c in range(n_cams):
        p = os.path.join(scene_dir, "intrinsics", f"{c}.txt")
        if os.path.exists(p):
            Ks[c], _ = load_K(p)

    per_frame = defaultdict(list)
    for iid, v in info.items():
        fa = v["frame_annotations"]
        for f, o2w, bs in zip(fa["frame_idx"], fa["obj_to_world"], fa["box_size"]):
            per_frame[f].append((iid, v["class_name"], o2w, bs))

    sw, sh = int(W * scale), int(H * scale)
    obs = defaultdict(list)

    for f, items in per_frame.items():
        for cam, K in Ks.items():
            ep = os.path.join(scene_dir, "extrinsics", f"{f:03d}_{cam}.txt")
            if not os.path.exists(ep):
                continue
            w2c = np.linalg.inv(load_mat(ep))
            drawn = []
            for iid, cls, o2w, bs in items:
                hull, depth, frac_in = project_hull(corners_world(o2w, bs), w2c, K, W, H, scale)
                if hull is None or len(hull) < 3:
                    continue
                drawn.append((depth, iid, cls, hull, frac_in, bs))
            if not drawn:
                continue
            # 画家算法：由远及近
            drawn.sort(key=lambda t: -t[0])
            idbuf = Image.new("I", (sw, sh), 0)
            dr = ImageDraw.Draw(idbuf)
            index = {}
            for k, (depth, iid, cls, hull, frac_in, bs) in enumerate(drawn, start=1):
                index[k] = (iid, cls, depth, hull, frac_in, bs)
                dr.polygon(hull, fill=k)
            arr = np.asarray(idbuf)
            counts = np.bincount(arr.ravel(), minlength=len(drawn) + 1)

            for k, (iid, cls, depth, hull, frac_in, bs) in index.items():
                if not cls.startswith(PED_PREFIX):
                    continue
                solo = Image.new("1", (sw, sh), 0)
                ImageDraw.Draw(solo).polygon(hull, fill=1)
                alone = int(np.asarray(solo).sum())
                if alone <= 0:
                    continue
                visible = int(counts[k]) if k < len(counts) else 0
                obs[iid].append({
                    "frame": int(f), "cam": int(cam), "depth": depth,
                    "alone_px": alone, "visible_px": visible,
                    "visible_fraction": min(1.0, visible / alone),
                    "in_frame_fraction": frac_in,
                })

    out = []
    for iid, v in info.items():
        if not v["class_name"].startswith(PED_PREFIX):
            continue
        o = obs.get(iid, [])
        if not o:
            out.append({"instance_id": iid, "class_name": v["class_name"], "n_observations": 0})
            continue
        vf = np.array([x["visible_fraction"] for x in o])
        ap = np.array([x["alone_px"] for x in o], dtype=float)
        # 以未遮挡面积加权，避免远处小目标的极端比例主导
        wmean = float((vf * ap).sum() / ap.sum())
        out.append({
            "instance_id": iid, "class_name": v["class_name"],
            "n_observations": len(o),
            "visible_fraction_median": float(np.median(vf)),
            "visible_fraction_p10": float(np.percentile(vf, 10)),
            "visible_fraction_area_weighted": wmean,
            "frac_obs_below_50pct_visible": float((vf < 0.5).mean()),
            "frac_obs_below_25pct_visible": float((vf < 0.25).mean()),
            "best_view_visible_fraction": float(vf.max()),
            "in_frame_fraction_median": float(np.median([x["in_frame_fraction"] for x in o])),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-cams", type=int, default=6)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--scale", type=float, default=0.5, help="光栅化降采样比例")
    a = ap.parse_args()
    res = {}
    for s in sorted(os.listdir(a.root)):
        sd = os.path.join(a.root, s)
        if not os.path.isdir(sd) or not os.path.exists(os.path.join(sd, "instances")):
            continue
        res[s] = analyse_scene(sd, a.n_cams, a.width, a.height, a.scale)
        print(f"scene {s}: {len(res[s])} pedestrians", flush=True)
    json.dump(res, open(a.out, "w"), indent=2)
    print("written", a.out)


if __name__ == "__main__":
    main()
