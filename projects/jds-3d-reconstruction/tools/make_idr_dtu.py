"""把 2DGS 版 DTU 转成 LOTree/GS-Octree 需要的 IDR 格式。

为什么需要转换：2DGS 包里 cameras.npz 的主点是 (823.2, 619.1)，对应 DTU 原始的
1600x1200 rectified 图；而 images/ 是 COLMAP 去畸变后的 1554x1162，主点 (777, 581)。
焦距两者完全相同（2892.33, 2883.18），且 1600-1554=46、1200-1162=38 恰好等于主点差，
说明去畸变在这里是**纯裁剪**，没有缩放、没有真正的畸变校正。

因此可以在本地精确地把相机矩阵搬到裁剪后的坐标系：P_new = T @ P_old，
T 为平移 (-dx, -dy)。mask 同样裁剪。这样 LOTree 与 MGSR 看到的是同一批像素，
两条管线的结果可比——比另外下载一份 IDR 版 DTU 更可靠。
"""
import numpy as np, os, sys
import imageio.v2 as imageio

src = sys.argv[1]          # .../2DGS_data/DTU/scanNN
dst = sys.argv[2]          # 输出目录
os.makedirs(f"{dst}/image", exist_ok=True)
os.makedirs(f"{dst}/mask", exist_ok=True)

cam = dict(np.load(f"{src}/cameras.npz"))
n = sum(1 for k in cam if k.startswith("world_mat_") and "inv" not in k)

imgs = sorted(f for f in os.listdir(f"{src}/images") if f.endswith((".png", ".jpg")) and not f.startswith("._"))
msks = sorted(f for f in os.listdir(f"{src}/mask") if f.endswith((".png", ".jpg")) and not f.startswith("._"))
assert len(imgs) == len(msks) == n, (len(imgs), len(msks), n)

im0 = imageio.imread(f"{src}/images/{imgs[0]}")
mk0 = imageio.imread(f"{src}/mask/{msks[0]}")
H, W = im0.shape[:2]
Hm, Wm = mk0.shape[:2]
dy, dx = Hm - H, Wm - W
assert dx >= 0 and dy >= 0, "去畸变图不应大于原图"
print(f"image {W}x{H} | mask {Wm}x{Hm} | 裁剪偏移 dx={dx} dy={dy}")

T = np.eye(4); T[0, 2] = -dx; T[1, 2] = -dy   # 主点平移

out = {}
for i in range(n):
    out[f"world_mat_{i}"] = T @ cam[f"world_mat_{i}"]
    out[f"scale_mat_{i}"] = cam[f"scale_mat_{i}"]
    out[f"scale_mat_inv_{i}"] = cam[f"scale_mat_inv_{i}"]
np.savez(f"{dst}/cameras_sphere.npz", **out)

for i, (a, b) in enumerate(zip(imgs, msks)):
    im = imageio.imread(f"{src}/images/{a}")[..., :3]          # 丢掉 alpha
    mk = imageio.imread(f"{src}/mask/{b}")[dy:, dx:][:H, :W]   # 与图对齐地裁剪
    if mk.ndim == 2: mk = np.repeat(mk[..., None], 3, -1)
    imageio.imwrite(f"{dst}/image/{i:04d}.png", im)
    imageio.imwrite(f"{dst}/mask/{i:03d}.png", mk[..., :3])
print(f"写出 {n} 组 -> {dst}")

# 自检：新主点应与 COLMAP 报告的一致
import cv2
P = (out["world_mat_0"] @ cam["scale_mat_0"])[:3, :4]
K = cv2.decomposeProjectionMatrix(P)[0]; K = K / K[2, 2]
print(f"自检 新主点 cx,cy = {K[0,2]:.1f}, {K[1,2]:.1f}  (应约等于 {W/2:.0f}, {H/2:.0f})")
