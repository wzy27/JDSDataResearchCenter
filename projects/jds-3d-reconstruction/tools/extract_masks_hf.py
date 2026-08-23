"""用 HuggingFace SegFormer 生成 sky mask 与 fine dynamic masks。

替代上游 datasets/tools/extract_masks.py。上游依赖 mmcv-full==1.2.7 + pytorch 1.8 + cu111，
而 cu111 最高支持 sm_86，在 RTX 4090 (sm_89) 上无法运行。本实现使用同一权重
(nvidia/segformer-b5-finetuned-cityscapes-1024-1024) 的 HuggingFace 版本，
配合本环境的 torch 2.0.0+cu118。

输出格式与上游严格一致：
  sky_masks/{fbase}.png                 = (class == 10) * 255
  fine_dynamic_masks/human/{fbase}.png  = (class in [11,12,17,18]) AND rough_human * 255
  fine_dynamic_masks/vehicle/{fbase}.png= (class in [13,14,15])   AND rough_vehicle * 255
  fine_dynamic_masks/all/{fbase}.png    = human OR vehicle * 255

GPU 使用受 gpu_budget.DutyThrottle 与 MemoryCap 限制。
"""
import argparse, os, sys, time
from glob import glob
import numpy as np
import torch
import imageio.v2 as imageio
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

# gpu_budget 随 gpu-budget skill 一起分发；相对本文件定位仓库根。
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "gpu-budget", "scripts"))
from gpu_budget import MemoryCap, DutyThrottle

MODEL_ID = "nvidia/segformer-b5-finetuned-cityscapes-1024-1024"
SKY = [10]
HUMAN = [11, 12, 17, 18]
VEHICLE = [13, 14, 15]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--scenes", default=None, help="逗号分隔场景名；默认全部")
    ap.add_argument("--process-dynamic-mask", action="store_true")
    ap.add_argument("--duty", type=float, default=0.6)
    ap.add_argument("--mem-fraction", type=float, default=0.6)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--infer-size", type=int, default=1024)
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()

    cap = MemoryCap(a.mem_fraction).apply()
    print(f"[budget] 显存上限 {cap['cap_gb']} GB / {cap['total_gb']} GB, 目标占空比 {a.duty}", flush=True)

    proc = SegformerImageProcessor.from_pretrained(MODEL_ID)
    model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID).cuda().eval()
    id2label = model.config.id2label
    assert id2label[10].lower() == "sky", f"类别 10 不是 sky，而是 {id2label[10]}"
    print(f"[model] {MODEL_ID}  类别数={len(id2label)}  class10={id2label[10]}", flush=True)

    scenes = sorted(a.scenes.split(",")) if a.scenes else \
        sorted(d for d in os.listdir(a.data_root) if os.path.isdir(os.path.join(a.data_root, d)))
    thr = DutyThrottle(target=a.duty)
    t_start = time.time()
    total = 0

    for sid in scenes:
        sdir = os.path.join(a.data_root, sid)
        img_dir = os.path.join(sdir, "images")
        if not os.path.isdir(img_dir):
            continue
        sky_dir = os.path.join(sdir, "sky_masks")
        os.makedirs(sky_dir, exist_ok=True)
        if a.process_dynamic_mask:
            for k in ("all", "human", "vehicle"):
                os.makedirs(os.path.join(sdir, "fine_dynamic_masks", k), exist_ok=True)

        flist = sorted(glob(os.path.join(img_dir, "*")))
        if a.skip_existing:   # 逐文件断点续跑
            n0 = len(flist)
            flist = [f for f in flist if not os.path.exists(os.path.join(
                sky_dir, os.path.splitext(os.path.basename(f))[0] + ".png"))]
            if not flist:
                print(f"[skip] {sid} 已完整", flush=True)
                continue
            if len(flist) < n0:
                print(f"[resume] {sid}: 跳过已完成 {n0 - len(flist)}，剩余 {len(flist)}", flush=True)

        done = 0
        for i in range(0, len(flist), a.batch):
            chunk = flist[i:i + a.batch]
            imgs, bases, sizes = [], [], []
            for fp in chunk:
                im = Image.open(fp).convert("RGB")
                imgs.append(im)
                sizes.append((im.size[1], im.size[0]))
                bases.append(os.path.splitext(os.path.basename(fp))[0])
            inputs = proc(images=imgs, return_tensors="pt")
            inputs = {k: v.cuda() for k, v in inputs.items()}
            with thr:
                with torch.no_grad():
                    logits = model(**inputs).logits
                ups = [torch.nn.functional.interpolate(
                    logits[j:j + 1], size=sizes[j], mode="bilinear", align_corners=False
                ).argmax(1)[0].to(torch.uint8).cpu().numpy() for j in range(len(chunk))]

            for j, base in enumerate(bases):
                m = ups[j]
                imageio.imwrite(os.path.join(sky_dir, f"{base}.png"),
                                np.isin(m, SKY).astype(np.uint8) * 255)
                if a.process_dynamic_mask:
                    rh = os.path.join(sdir, "dynamic_masks", "human", f"{base}.png")
                    rv = os.path.join(sdir, "dynamic_masks", "vehicle", f"{base}.png")
                    if os.path.exists(rh) and os.path.exists(rv):
                        rough_h = imageio.imread(rh) > 0
                        rough_v = imageio.imread(rv) > 0
                        vh = np.logical_and(np.isin(m, HUMAN), rough_h)
                        vv = np.logical_and(np.isin(m, VEHICLE), rough_v)
                        imageio.imwrite(os.path.join(sdir, "fine_dynamic_masks", "human", f"{base}.png"),
                                        vh.astype(np.uint8) * 255)
                        imageio.imwrite(os.path.join(sdir, "fine_dynamic_masks", "vehicle", f"{base}.png"),
                                        vv.astype(np.uint8) * 255)
                        imageio.imwrite(os.path.join(sdir, "fine_dynamic_masks", "all", f"{base}.png"),
                                        np.logical_or(vh, vv).astype(np.uint8) * 255)
            done += len(chunk)
            total += len(chunk)
            if done % 200 < a.batch:
                el = time.time() - t_start
                print(f"[{sid}] {done}/{len(flist)}  duty={thr.measured_duty:.3f}  "
                      f"{total/el:.1f} img/s  elapsed={el/60:.1f}min", flush=True)
        print(f"[done] {sid}: {done} images", flush=True)

    print(f"[budget] {thr.summary()}", flush=True)
    print(f"[total] {total} images in {(time.time()-t_start)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
