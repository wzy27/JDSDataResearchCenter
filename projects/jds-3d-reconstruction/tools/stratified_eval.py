"""按分层报告 human-region 的 PSNR/SSIM。

与 DriveStudio 内置的 human_psnr 的区别：内置指标把一帧内所有行人的像素合并成一个
mask 后取全局值，因此远处小目标被近处大目标淹没。本脚本按实例切分，再按
(有效像素分辨率 x 可见比) 分层聚合，使远距/高遮挡组的退化可见。

预测图来自 DriveStudio `save_images=True` 导出的逐帧 PNG。
真值与 human mask 取自 processed 场景目录。
"""
import argparse, json, os
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw
from skimage.metrics import structural_similarity as ssim_fn

PED_PREFIX = ("human.pedestrian",)


def load_mat(p): return np.loadtxt(p).reshape(4, 4)


def load_K(p, sx=1.0, sy=1.0):
    """按图像缩放比例同步缩放内参；否则投影会落到画布之外。"""
    v = np.loadtxt(p)
    return np.array([[v[0] * sx, 0, v[2] * sx],
                     [0, v[1] * sy, v[3] * sy],
                     [0, 0, 1]])


def corners_world(o2w, size):
    w, l, h = size
    pts = np.array([[x, y, z, 1.0]
                    for x in (-l / 2, l / 2) for y in (-w / 2, w / 2) for z in (-h / 2, h / 2)]).T
    return (np.asarray(o2w) @ pts)[:3].T


def hull_mask(corners, w2c, K, W, H):
    pts = np.hstack([corners, np.ones((len(corners), 1))])
    cam = (w2c @ pts.T).T[:, :3]
    front = cam[:, 2] > 0.1
    if front.sum() < 3:
        return None
    uv = (K @ cam[front].T).T
    uv = uv[:, :2] / uv[:, 2:3]
    if not (((uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)).any()):
        return None
    try:
        from scipy.spatial import ConvexHull
        poly = uv[ConvexHull(uv).vertices]
    except Exception:
        poly = uv
    m = Image.new("1", (W, H), 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
    return np.asarray(m)


def exclusive_instance_masks(annotations, w2c, K, W, H):
    """按深度排序生成互斥的 per-instance 掩码：重叠像素归属最近的实例。

    annotations: [(instance_id, obj_to_world, box_size), ...]
    返回 [(instance_id, mask), ...]，近 -> 远。
    """
    cand = []
    for iid, o2w, bs in annotations:
        cw = corners_world(o2w, bs)
        pts = np.hstack([cw, np.ones((len(cw), 1))])
        z = (w2c @ pts.T).T[:, 2]
        zf = z[z > 0.1]
        if zf.size < 3:
            continue
        hm = hull_mask(cw, w2c, K, W, H)
        if hm is None:
            continue
        cand.append((float(zf.min()), iid, hm))
    cand.sort(key=lambda t: t[0])
    claimed = np.zeros((H, W), bool)
    out = []
    for _, iid, hm in cand:
        out.append((iid, hm & ~claimed))
        claimed |= hm
    return out


def psnr_on(pred, gt, mask):
    if mask.sum() < 1:
        return None
    mse = float(np.mean((pred[mask] - gt[mask]) ** 2))
    if mse <= 1e-12:
        return None  # 完全一致，不纳入统计
    return float(-10.0 * np.log10(mse))


def evaluate(scene_dir, pred_dir, strata, frame_ids, cam_ids, W, H,
             native_W=1600, native_H=900, ssim_full=True, mask_source="coarse"):
    """mask_source: 'coarse' 用 dynamic_masks/human（3D box 投影，偏大）；
    'fine' 用 fine_dynamic_masks/human（语义分割 ∩ 粗掩码，边界更准）；
    'hull' 只用 3D box 凸包，不与任何 human mask 求交。"""
    info = json.load(open(os.path.join(scene_dir, "instances", "instances_info.json")))
    sx, sy = W / float(native_W), H / float(native_H)
    Ks = {c: load_K(os.path.join(scene_dir, "intrinsics", f"{c}.txt"), sx, sy) for c in cam_ids
          if os.path.exists(os.path.join(scene_dir, "intrinsics", f"{c}.txt"))}
    ann = defaultdict(list)
    for iid, v in info.items():
        if not v["class_name"].startswith(PED_PREFIX):
            continue
        fa = v["frame_annotations"]
        for f, o2w, bs in zip(fa["frame_idx"], fa["obj_to_world"], fa["box_size"]):
            ann[f].append((iid, o2w, bs))

    per_instance = defaultdict(lambda: {"psnr": [], "ssim": [], "px": 0})
    per_obs = []          # 逐观测记录，供 E2 的观测级分析使用
    missing = []
    for fi, f in enumerate(frame_ids):
        for ci, cam in enumerate(cam_ids):
            pp = os.path.join(pred_dir, f"{fi:03d}_{ci:03d}.png")
            gp = os.path.join(scene_dir, "images", f"{f:03d}_{cam}.jpg")
            if mask_source == "fine":
                hp = os.path.join(scene_dir, "fine_dynamic_masks", "human", f"{f:03d}_{cam}.png")
            else:
                hp = os.path.join(scene_dir, "dynamic_masks", "human", f"{f:03d}_{cam}.png")
            if not (os.path.exists(pp) and os.path.exists(gp)):
                missing.append((f, cam))
                continue
            pred = np.asarray(Image.open(pp).convert("RGB").resize((W, H))).astype(np.float64) / 255.0
            gt = np.asarray(Image.open(gp).convert("RGB").resize((W, H))).astype(np.float64) / 255.0
            human = (np.asarray(Image.open(hp).convert("L").resize((W, H))) > 0) if os.path.exists(hp) \
                else np.ones((H, W), bool)
            smap = None
            if ssim_full:
                smap = ssim_fn(gt, pred, data_range=1.0, channel_axis=-1, full=True)[1].mean(-1)
            ep = os.path.join(scene_dir, "extrinsics", f"{f:03d}_{cam}.txt")
            if not os.path.exists(ep) or cam not in Ks:
                continue
            w2c = np.linalg.inv(load_mat(ep))
            exclusive = exclusive_instance_masks(ann.get(f, []), w2c, Ks[cam], W, H)
            if not exclusive:
                continue
            for iid, hm in exclusive:
                m = hm & human           # 用真值 human mask 收紧到实际人体像素
                if m.sum() < max(4, int(16 * sx * sy)):  # 像素过少的观测不纳入统计
                    continue
                p = psnr_on(pred, gt, m)
                if p is not None:
                    per_instance[iid]["psnr"].append(p)
                sv = float(smap[m].mean()) if smap is not None else None
                if sv is not None:
                    per_instance[iid]["ssim"].append(sv)
                per_instance[iid]["px"] += int(m.sum())
                # 该次观测自身的投影高度（渲染分辨率下），用于观测级分层
                ys, xs = np.nonzero(m)
                per_obs.append({
                    "instance_id": iid, "frame": int(f), "cam": int(cam),
                    "psnr": p, "ssim": sv, "px": int(m.sum()),
                    "obs_px_height": int(ys.max() - ys.min() + 1) if ys.size else 0,
                })

    cells = defaultdict(lambda: {"psnr": [], "ssim": [], "instances": 0, "px": 0})
    for iid, d in per_instance.items():
        s = strata.get(iid)
        if not s or not d["psnr"]:
            continue
        c = cells[s["cell"]]
        c["psnr"].append(float(np.mean(d["psnr"])))
        if d["ssim"]:
            c["ssim"].append(float(np.mean(d["ssim"])))
        c["instances"] += 1
        c["px"] += d["px"]

    out = {}
    for k, v in cells.items():
        out[k] = {"instances": v["instances"], "pixels": v["px"],
                  "psnr_mean": round(float(np.mean(v["psnr"])), 4),
                  "psnr_std": round(float(np.std(v["psnr"])), 4),
                  "ssim_mean": round(float(np.mean(v["ssim"])), 4) if v["ssim"] else None}
    return {"cells": out, "n_instances_scored": len(per_instance),
            "missing_frames": len(missing), "mask_source": mask_source,
            "observations": per_obs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene-dir", required=True)
    ap.add_argument("--pred-dir", required=True)
    ap.add_argument("--strata", required=True)
    ap.add_argument("--scene-key", required=True)
    ap.add_argument("--frame-ids", required=True, help="逗号分隔，或 range:start:stop:step")
    ap.add_argument("--cam-ids", default="0,1,2,3,4,5")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--obs-out", default=None,
                    help="另存逐观测记录（E2 观测级分析所需）")
    ap.add_argument("--mask-sources", default="coarse,fine",
                    help="逗号分隔，可选 coarse / fine / hull；多个则同时报告以作对照")
    ap.add_argument("--native-width", type=int, default=1600)
    ap.add_argument("--native-height", type=int, default=900)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.frame_ids.startswith("range:"):
        _, s, e, st = a.frame_ids.split(":")
        frames = list(range(int(s), int(e), int(st)))
    else:
        frames = [int(x) for x in a.frame_ids.split(",")]
    cams = [int(x) for x in a.cam_ids.split(",")]
    strata = json.load(open(a.strata))[a.scene_key]
    results = {}
    for src in [x.strip() for x in a.mask_sources.split(",") if x.strip()]:
        results[src] = evaluate(a.scene_dir, a.pred_dir, strata, frames, cams,
                                a.width, a.height, a.native_width, a.native_height,
                                mask_source=src)
    if a.obs_out:
        json.dump({k: v["observations"] for k, v in results.items()},
                  open(a.obs_out, "w"))
        print("per-observation records ->", a.obs_out)
    slim = {k: {kk: vv for kk, vv in v.items() if kk != "observations"}
            for k, v in results.items()}
    json.dump(slim, open(a.out, "w"), indent=2)
    # 对照表
    srcs = list(results)
    cells = sorted({c for r in results.values() for c in r["cells"]})
    print("%-26s" % "cell" + "".join("%18s" % s for s in srcs))
    for c in cells:
        row = "%-26s" % c
        for s_ in srcs:
            v = results[s_]["cells"].get(c)
            row += "%18s" % (("%.2f dB / %d" % (v["psnr_mean"], v["instances"])) if v else "-")
        print(row)
    for s_ in srcs:
        print("%s: scored=%d missing=%d" % (s_, results[s_]["n_instances_scored"],
                                            results[s_]["missing_frames"]))


if __name__ == "__main__":
    main()
