#!/usr/bin/env bash
# GS-Octree 完整两段式：LOTree 第一阶段（体渲染 SDF）-> train-big.py（高斯 + SDF 互导）
#
# 第一阶段产出 SDF_512_<scene>.npz / dict_512_<scene>.npy，train-big.py 必须先有它们。
# 第一阶段输出目录是脚本里硬编码的 ./output/<时间戳>，故运行后按时间戳定位。
set -u
source ~/miniforge3/etc/profile.d/conda.sh
conda activate lotree

SCENE=${1:-scan24}
M=~/fastrelight/mutual/lotree_main/LOTree-main
G=~/fastrelight/mutual/gs-octree
DATA=~/fastrelight/data/dtu_idr
OUT=~/fastrelight/mutual/out
PRE=~/fastrelight/mutual/pretrain
mkdir -p "$OUT/lotree_$SCENE" "$PRE"

echo "=== 阶段一 LOTreeOptGaussVolSDF $SCENE  $(date +%m-%d\ %H:%M) ==="
cd "$DATA"
export PYTHONPATH=$M
STAMP_BEFORE=$(ls output 2>/dev/null | wc -l)
python -u "$M/LOTreeOptGaussVolSDF.py" \
  --dataset dtu --data_dir1 "$SCENE" --data_dir "$SCENE" \
  --input "$OUT/lotree_$SCENE/tree.npz" --output "$OUT/lotree_$SCENE/tree_opt.npz" \
  > "$OUT/lotree_$SCENE.log" 2>&1
S1=$?
echo "阶段一退出码 $S1  $(date +%H:%M)"
grep -oE "PSNR=[0-9.]+" "$OUT/lotree_$SCENE.log" | tail -1
tail -5 "$OUT/lotree_$SCENE.log" | tr "\r" "\n" | tail -3

SDF=$(find "$DATA/output" -name "SDF_512_$SCENE.npz" -newermt "-1 day" | sort | tail -1)
if [ -z "$SDF" ]; then
  echo "!! 阶段一没有产出 SDF_512_$SCENE.npz，中止"
  echo "   output/ 下现有内容："; find "$DATA/output" -maxdepth 2 | tail -20
  exit 1
fi
D=$(dirname "$SDF")
cp "$SDF" "$D/dict_512_$SCENE.npy" "$PRE/"
echo "预训练 SDF 就位: $PRE/SDF_512_$SCENE.npz ($(du -h "$PRE/SDF_512_$SCENE.npz" | cut -f1))"

echo
echo "=== 阶段二 train-big.py  $(date +%H:%M) ==="
echo "    30000 x 6 epochs + 5000 final = 185000 步"
cd "$G"
export PYTHONPATH="$G:$M"
export GSO_PRETRAIN_DIR="$PRE"
export GSO_LOT_DATASET=dtu
python -u train-big.py --eval \
  -s "$DATA/$SCENE" \
  -m "$OUT/gso_$SCENE" \
  --sh_degree 0 --lambda_opacity 3 --lambda_orientation 0 --lambda_scale 0.1 \
  --opacity_scalar 200 --near_threshold 0.01 --hessian_eikonal -w \
  > "$OUT/gso_$SCENE.log" 2>&1
echo "阶段二退出码 $?  $(date +%H:%M)"
tail -6 "$OUT/gso_$SCENE.log" | tr "\r" "\n" | tail -4
