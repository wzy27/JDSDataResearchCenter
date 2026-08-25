#!/usr/bin/env bash
# 把 ref 支的最优点夹出来。
#
# 已确立（判据写于 §16.4，早于数据）：w=0.05 在三种子上均优于 w=0.01，
# 幅度 3.40/3.08/2.72%，均值 -3.07%（17.0 倍基线 sd）。判据一命中。
# 但补跑的 w=0.1（n=1）得 1.1847，比 0.05 更好（-4.17%），
# 说明最优点在 0.1 或更右，MGSR 的 0.01 至少小 10 倍。
#
# 本轮：把 w=0.1 提到 n=3，并向右探 0.2 与 0.3，确定拐点位置。
# 0.5 已知劣化 +5.40%，故拐点必在 (0.1, 0.5) 之间。
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

run_one () {
  local S=$1 W=$2 TAG=$3
  echo
  echo "=== seed=$S w_depth=$W  开始 $(date +%m-%d\ %H:%M) ==="
  export MGSR_SEED=$S
  export MGSR_W_DEPTH=$W
  cd "$M"
  python -u train.py -s "$D" -m "$OUT/$TAG" -r 2 --eval > "$OUT/$TAG.log" 2>&1
  echo "退出码 $?  $(date +%H:%M)"
}

# 先把 w=0.1 提到 n=3——它目前是最优候选，优先级最高
run_one 1 0.1 s1_w01
run_one 2 0.1 s2_w01
# 再向右探，确定拐点
run_one 0 0.2 s0_w02
run_one 0 0.3 s0_w03

echo
echo "=== 夹逼轮结束 $(date +%m-%d\ %H:%M) ==="
