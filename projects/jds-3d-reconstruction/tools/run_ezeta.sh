#!/usr/bin/env bash
# E-zeta：扫描 MGSR 中 geo->ref 通道的权重。
#
# 原代码：total_loss = 0.5*loss_ref + 0.01*depth_loss + 0.5*loss_n
# 0.01 是 geo->ref 的全部强度，与 ref->geo 的有效强度 0.5*0.2=0.1 相差十倍。
# 该取值论文未讨论、未消融。本扫描给出「渲染 x 几何」平面上的前沿。
#
# 每个点复用 2026-08-24 那次跑出的 geo/ref 检查点，只跑互导 20k 步。
# 显存限到 0.55（约 13.5 GB），占空比由 AdaptiveBudget 按前台负载自适应。
set -u
source ~/miniforge3/etc/profile.d/conda.sh
conda activate MGSR

M=~/fastrelight/mutual/MGSR
D=~/fastrelight/data/dtu2dgs/2DGS_data/DTU/scan24
CK=~/fastrelight/mutual/out/dtu_scan24
OUT=~/fastrelight/mutual/out/ezeta

export MGSR_ONLY_TOTAL=1
export MGSR_CKPT_DIR="$CK"
export MGSR_MEM_FRAC=0.55

# 先跑两个极端点。若几何毫无变化，就是「前沿平坦」那一支结论，能最快得到。
for W in 0.5 0.001 0.05; do
  TAG=$(echo "$W" | tr -d '.')
  echo
  echo "=================================================="
  echo "=== w_depth=$W  开始 $(date +%m-%d\ %H:%M) ==="
  echo "=================================================="
  export MGSR_W_DEPTH=$W
  cd "$M"
  python -u train.py -s "$D" -m "$OUT/w$TAG" -r 2 --eval \
    > "$OUT/w$TAG.log" 2>&1
  echo "退出码 $?  $(date +%H:%M)"
  tail -3 "$OUT/w$TAG.log" | tr '\r' '\n' | tail -2
  if [ -f "$OUT/w$TAG/total/ezeta_trace.tsv" ]; then
    echo "--- trace 末行 ---"; tail -2 "$OUT/w$TAG/total/ezeta_trace.tsv"
  fi
done
echo
echo "=== E-zeta 扫描结束 $(date +%m-%d\ %H:%M) ==="
