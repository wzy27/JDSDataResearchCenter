#!/usr/bin/env bash
# E-zeta 的种子重复：唯一目的是回答「w=0.5 时 ref 支劣化 6.6% 是否超出 run-to-run 波动」。
#
# 首轮三个权重点共用 seed=0（safe_state 原写死），因此权重比较干净，
# 但完全没有波动估计。本轮在 seed=1、2 上重跑 w=0.01 与 w=0.5 两个关键点：
#
#   * 若两个种子下 w=0.5 都比 w=0.01 差且幅度相近 -> 效应真实；
#   * 若同一权重在不同种子间的散布就有 5-6% -> 首轮结论作废。
#
# 顺序按「先拿到最有判别力的一对」排：seed1 的两点跑完就能初判。
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

for S in 1 2; do
  for W in 0.01 0.5; do
    TAG="s${S}_w$(echo "$W" | tr -d '.')"
    echo
    echo "=================================================="
    echo "=== seed=$S w_depth=$W  开始 $(date +%m-%d\ %H:%M) ==="
    echo "=================================================="
    export MGSR_SEED=$S
    export MGSR_W_DEPTH=$W
    cd "$M"
    python -u train.py -s "$D" -m "$OUT/$TAG" -r 2 --eval > "$OUT/$TAG.log" 2>&1
    echo "退出码 $?  $(date +%H:%M)"
  done
done
echo
echo "=== 种子重复结束 $(date +%m-%d\ %H:%M) ==="
