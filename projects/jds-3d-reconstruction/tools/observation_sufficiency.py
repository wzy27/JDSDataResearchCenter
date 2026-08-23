"""按距离、投影像素高度、观测次数与遮挡代理，统计驾驶数据中行人的观测充分性。

只读取标注与标定，不训练、不渲染、不使用 GPU。
输出用于设计 EXP-D364146FE7A6 的分层轴。
"""
import argparse, json, os
from collections import defaultdict
import numpy as np

PED_PREFIX = ("human.pedestrian",)


def load_mat(path):
    return np.loadtxt(path).reshape(4, 4)


def load_intrinsics(path):
    v = np.loadtxt(path)
    fx, fy, cx, cy = v[0], v[1], v[2], v[3]
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    return K, fy


def box_corners_world(obj_to_world, box_size):
    """box_size 为 (w, l, h)，返回 8 个角点的世界坐标。"""
    w, l, h = box_size
    xs = np.array([-1, 1]) * l / 2
    ys = np.array([-1, 1]) * w / 2
    zs = np.array([-1, 1]) * h / 2
    pts = np.array([[x, y, z, 1.0] for x in xs for y in ys for z in zs]).T
    return (np.asarray(obj_to_world) @ pts)[:3].T


def project(points_world, world_to_cam, K, W, H):
    """返回 (在视锥内的点数, 像素框 或 None, 中心深度)。"""
    pts = np.hstack([points_world, np.ones((len(points_world), 1))])
    cam = (world_to_cam @ pts.T).T[:, :3]
    front = cam[:, 2] > 0.1
    if not front.any():
        return 0, None, np.inf
    c = cam[front]
    uv = (K @ c.T).T
    uv = uv[:, :2] / uv[:, 2:3]
    inside = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    if not inside.any():
        return 0, None, float(np.median(c[:, 2]))
    bbox = (uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:, 1].max())
    return int(inside.sum()), bbox, float(np.median(c[:, 2]))


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    area_a = max((a[2] - a[0]) * (a[3] - a[1]), 1e-6)
    return inter / area_a


def analyse_scene(scene_dir, n_cams, W, H):
    info = json.load(open(os.path.join(scene_dir, "instances", "instances_info.json")))
    Ks, fys = {}, {}
    for c in range(n_cams):
        p = os.path.join(scene_dir, "intrinsics", f"{c}.txt")
        if os.path.exists(p):
            Ks[c], fys[c] = load_intrinsics(p)

    # 缓存每帧每相机的 world_to_cam
    w2c_cache = {}

    def w2c(frame, cam):
        key = (frame, cam)
        if key not in w2c_cache:
            p = os.path.join(scene_dir, "extrinsics", f"{frame:03d}_{cam}.txt")
            w2c_cache[key] = np.linalg.inv(load_mat(p)) if os.path.exists(p) else None
        return w2c_cache[key]

    # 预先把所有实例按帧组织，用于遮挡代理
    per_frame = defaultdict(list)  # frame -> [(iid, class, o2w, size)]
    for iid, v in info.items():
        fa = v["frame_annotations"]
        for f, o2w, bs in zip(fa["frame_idx"], fa["obj_to_world"], fa["box_size"]):
            per_frame[f].append((iid, v["class_name"], o2w, bs))

    results = []
    for iid, v in info.items():
        if not v["class_name"].startswith(PED_PREFIX):
            continue
        fa = v["frame_annotations"]
        obs = []
        for f, o2w, bs in zip(fa["frame_idx"], fa["obj_to_world"], fa["box_size"]):
            corners = box_corners_world(o2w, bs)
            for cam in Ks:
                M = w2c(f, cam)
                if M is None:
                    continue
                n_in, bbox, depth = project(corners, M, Ks[cam], W, H)
                if n_in == 0 or bbox is None:
                    continue
                px_h = fys[cam] * bs[2] / max(depth, 1e-6)
                # 遮挡代理：同帧同相机中更近的其他 box 对本 box 像素框的覆盖比
                occ = 0.0
                for jid, _, jo2w, jbs in per_frame[f]:
                    if jid == iid:
                        continue
                    jc = box_corners_world(jo2w, jbs)
                    jn, jbox, jdepth = project(jc, M, Ks[cam], W, H)
                    if jn == 0 or jbox is None or jdepth >= depth:
                        continue
                    occ = max(occ, iou(bbox, jbox))
                obs.append({"frame": int(f), "cam": int(cam), "depth": depth,
                            "px_height": float(px_h), "occlusion_proxy": float(occ)})
        if not obs:
            results.append({"instance_id": iid, "class_name": v["class_name"],
                            "n_observations": 0, "n_frames": 0})
            continue
        d = np.array([o["depth"] for o in obs])
        ph = np.array([o["px_height"] for o in obs])
        oc = np.array([o["occlusion_proxy"] for o in obs])
        results.append({
            "instance_id": iid,
            "class_name": v["class_name"],
            "n_observations": len(obs),
            "n_frames": len({o["frame"] for o in obs}),
            "n_cameras": len({o["cam"] for o in obs}),
            "depth_min": float(d.min()), "depth_median": float(np.median(d)),
            "px_height_max": float(ph.max()), "px_height_median": float(np.median(ph)),
            "occlusion_proxy_median": float(np.median(oc)),
            "occlusion_proxy_max": float(oc.max()),
        })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-cams", type=int, default=6)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()

    all_res = {}
    for s in sorted(os.listdir(a.root)):
        sd = os.path.join(a.root, s)
        if not os.path.isdir(sd) or not os.path.exists(os.path.join(sd, "instances")):
            continue
        r = analyse_scene(sd, a.n_cams, a.width, a.height)
        all_res[s] = r
        print(f"scene {s}: {len(r)} pedestrian instances")
    json.dump(all_res, open(a.out, "w"), indent=2)
    print("written", a.out)


if __name__ == "__main__":
    main()
