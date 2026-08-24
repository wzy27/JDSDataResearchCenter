#!/usr/bin/env bash
# 确认 ref 支几何在 w_depth 上的内部最优点。
#
# 已确立（seed 0/1/2，n=3）：
#   ref overall  w=0.01 -> 1.2363 +- 0.0022   |   w=0.5 -> 1.3031 +- 0.0108
#   噪声地板（同权重跨种子散布）0.36%，因此 5.4% 的劣化远超噪声。
#   seed 0 下 w=0.05 得 1.1919，比基线均值低 3.6%，约 20 个标准差——但 n=1。
#
# 本轮两件事：
#   1. w=0.05 在 seed 1、2 上复现，把最优点从 n=1 提到 n=3；
#   2. 补 w=0.1（seed 0），判断 0.05 与 0.5 之间曲线怎么转向。
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
  echo "=================================================="
  echo "=== seed=$S w_depth=$W  开始 $(date +%m-%d\ %H:%M) ==="
  echo "=================================================="
  export MGSR_SEED=$S
  export MGSR_W_DEPTH=$W
  cd "$M"
  python -u train.py -s "$D" -m "$OUT/$TAG" -r 2 --eval > "$OUT/$TAG.log" 2>&1
  echo "退出码 $?  $(date +%H:%M)"
}

run_one 1 0.05 s1_w005
run_one 2 0.05 s2_w005
run_one 0 0.1  s0_w01

echo
echo "=== 最优点确认轮结束 $(date +%m-%d\ %H:%M) ==="
