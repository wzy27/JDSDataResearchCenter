"""M3 v3：以跨帧体型一致性判定 HMR2 姿态是否可靠。

前两版失败的记录（务必保留，避免重蹈）：
  v1 判据「关节落在 crop 内比例 + 预测身高/box 高度」——与输入几乎无关，
     HMR2 对任何输入都输出填满 crop 的正常身高人体。破绽：0-64px 档 80% 通过。
  v2 判据「预测网格投影与人体掩码的轮廓 IoU」——掩码过稀导致 57% 实例无法判定
     且排除有偏；官方成功组 p10 低至 0.001 使阈值退化；IoU 不随分辨率单调。

v3 判据：同一行人在其多个观测上分别独立预测，比较预测体型（SMPL betas）
与预测身高的离散程度。同一个人的体型不随时间变化，因此
  离散度小 = 模型在稳定地估计该人体
  离散度大 = 模型在噪声上拟合，输出不可信
该量与输入质量强相关，不依赖分割掩码，也不需要真值姿态。
"""
import argparse, json, os, pickle, sys
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.expanduser("~/fastrelight/analysis"))
from adaptive_budget import AdaptiveBudget
ROOT = os.path.expanduser("~/fastrelight/drivestudio/data/nuscenes/processed_10Hz/mini")


def load_mat(p): return np.loadtxt(p).reshape(4, 4)
def load_K(p):
    v = np.loadtxt(p); return np.array([[v[0],0,v[2]],[0,v[1],v[3]],[0,0,1]])
def corners_world(o2w, size):
    w,l,h = size
    return (np.asarray(o2w) @ np.array(
        [[x,y,z,1.0] for x in (-l/2,l/2) for y in (-w/2,w/2) for z in (-h/2,h/2)]).T)[:3].T


def views(sdir, info, W, H, Ks, k):
    """取投影高度最大的 k 个观测（不同帧，避免同帧多相机的强相关）。"""
    fa = info["frame_annotations"]; cand = []
    for f, o2w, bs in zip(fa["frame_idx"], fa["obj_to_world"], fa["box_size"]):
        cw = corners_world(o2w, bs)
        best = None
        for cam in range(6):
            ep = os.path.join(sdir, "extrinsics", f"{f:03d}_{cam}.txt")
            if not os.path.exists(ep): continue
            p = np.hstack([cw, np.ones((8,1))])
            c = (np.linalg.inv(load_mat(ep)) @ p.T).T[:,:3]
            ok = c[:,2] > 0.1
            if ok.sum() < 3: continue
            uv = (Ks[cam] @ c[ok].T).T; uv = uv[:,:2]/uv[:,2:3]
            x0,y0,x1,y1 = uv[:,0].min(),uv[:,1].min(),uv[:,0].max(),uv[:,1].max()
            if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H: continue
            if best is None or (y1-y0) > best[2]:
                best = (int(cam), (x0,y0,x1,y1), y1-y0)
        if best: cand.append((int(f), best[0], best[1], best[2]))
    cand.sort(key=lambda t: -t[3])
    # 分散取样，避免相邻帧几乎相同
    picked, used = [], []
    for c in cand:
        if all(abs(c[0]-u) >= 5 for u in used):
            picked.append(c); used.append(c[0])
        if len(picked) >= k: break
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="000,001,008")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()

    from hmr2.models import load_hmr2, DEFAULT_CHECKPOINT
    from hmr2.utils import recursive_to
    from hmr2.datasets.vitdet_dataset import ViTDetDataset

    budget = AdaptiveBudget(mem_fraction=0.25).start()
    model, cfg = load_hmr2(DEFAULT_CHECKPOINT); model = model.cuda().eval()
    print("[m3v3] loaded", flush=True)
    STATS = json.load(open(os.path.expanduser("~/fastrelight/analysis/ped_observation_stats.json")))
    res = []
    for scene in a.scenes.split(","):
        sdir = os.path.join(ROOT, scene)
        Ks = {c: load_K(os.path.join(sdir,"intrinsics",f"{c}.txt")) for c in range(6)}
        infos = json.load(open(os.path.join(sdir,"instances","instances_info.json")))
        smpl = pickle.load(open(os.path.join(sdir,"humanpose","smpl.pkl"),"rb"))
        has = {str(k) for k,v in smpl.items()
               if isinstance(v,dict) and np.asarray(v["valid_mask"]).sum()>0}
        obs = {r["instance_id"]: r for r in STATS[scene] if r.get("n_observations",0)>0}
        for iid, rec in obs.items():
            vs = views(sdir, infos[iid], a.width, a.height, Ks, a.k)
            if len(vs) < 3: continue
            betas, heights, hpxs = [], [], []
            for f, cam, box, hpx in vs:
                ip = os.path.join(sdir,"images",f"{f:03d}_{cam}.jpg")
                if not os.path.exists(ip): continue
                img = np.array(Image.open(ip).convert("RGB"))
                x0,y0,x1,y1 = box
                bb = np.array([[max(0,x0),max(0,y0),min(a.width-1,x1),min(a.height-1,y1)]])
                ds = ViTDetDataset(cfg, img[:,:,::-1], bb)
                batch = recursive_to(next(iter(torch.utils.data.DataLoader(ds,batch_size=1))),"cuda")
                with budget():
                    with torch.no_grad():
                        out = model(batch)
                betas.append(out["pred_smpl_params"]["betas"][0].cpu().numpy())
                v = out["pred_vertices"][0].cpu().numpy()
                heights.append(float(v[:,1].max()-v[:,1].min()))
                hpxs.append(float(hpx))
            if len(betas) < 3: continue
            B = np.stack(betas)
            res.append({"scene":scene,"iid":iid,"has_pose_official":iid in has,
                        "n_views":len(B),
                        "px_height_native":round(float(np.max(hpxs)),1),
                        "px_height_render":round(float(np.max(hpxs))/3,1),
                        "beta_std_mean":round(float(B.std(0).mean()),4),
                        "beta_std_max":round(float(B.std(0).max()),4),
                        "height_std":round(float(np.std(heights)),4),
                        "height_mean":round(float(np.mean(heights)),4)})
            if len(res)%30==0:
                print("[m3v3] %d done duty=%s other=%s"%(len(res),budget.duty,budget.other_util),flush=True)
    budget.stop()
    json.dump({"budget":budget.summary(),"results":res},open(a.out,"w"),indent=2,ensure_ascii=False)
    print("[m3v3] %d -> %s"%(len(res),a.out)); print("[m3v3] budget:",budget.summary())


if __name__ == "__main__":
    main()
