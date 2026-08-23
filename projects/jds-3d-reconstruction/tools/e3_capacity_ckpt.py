"""E3：从训练后的 checkpoint 读各 node 的最终 Gaussian 容量。"""
import glob, os, torch, json
ck = sorted(glob.glob(os.path.expanduser("~/fastrelight/outputs/e1/e1_s000/checkpoint_*.pth")),
            key=lambda p: int(p.split("_")[-1].split(".")[0]))
if not ck:
    print("无 checkpoint"); raise SystemExit
p = ck[-1]
print("checkpoint:", os.path.basename(p))
sd = torch.load(p, map_location="cpu")
models = sd.get("models", sd)
out = {}
for name, m in (models.items() if isinstance(models, dict) else []):
    if not isinstance(m, dict): continue
    for k, v in m.items():
        if hasattr(v, "shape") and v.ndim >= 1 and ("means" in k or "_xyz" in k):
            out[name] = int(v.shape[0]); break
for k, v in sorted(out.items(), key=lambda x: -x[1]):
    print(f"  {k:20s} {v:9d} gaussians")
if "SMPLNodes" in out:
    print(f"  SMPLNodes / 6890 = {out['SMPLNodes']/6890:.1f} 个实例")
if "DeformableNodes" in out and "SMPLNodes" in out:
    print(f"  容量对比: SMPLNodes 每实例 6890 vs DeformableNodes 总计 {out['DeformableNodes']}")
json.dump(out, open(os.path.expanduser("~/fastrelight/analysis/e3_capacity_final.json"),"w"), indent=2)
