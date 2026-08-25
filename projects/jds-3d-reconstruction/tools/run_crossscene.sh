#!/usr/bin/env bash
# G1 阶段门：耦合强度的效应是否跨场景成立。
#
# scan24 上已确立（n=3 种子）：
#   ref 支在 w=0.05-0.2 改善约 3%（13-18 倍基线 sd），0.3 起劣于基线，0.5 劣化 5.40%；
#   geo 支在整个范围内落在噪声内。
# 但全部来自单一场景。若效应仅见于 scan24，则属场景特性而非机制，方向须重估。
#
# 通过判据（写于运行之前）：
#   至少 3/4 场景上，w=0.1 相对 w=0.01 的 ref 支改善 >=2% 且方向一致。
#
# 结构：每个场景先跑一次完整三阶段（60k 步，约 2 小时）拿到 geo/ref 检查点，
# 该次即 w=0.01 的基线；其余权重复用检查点只跑互导 20k 步（约 40 分钟）。
set -u
source ~/miniforge3/etc/profile.d/conda.sh
conda activate MGSR

M=~/fastrelight/mutual/MGSR
DR=~/fastrelight/data/dtu2dgs/2DGS_data/DTU
OUT=~/fastrelight/mutual/out/cross

mkdir -p "$OUT"
export MGSR_MEM_FRAC=0.55
export MGSR_SEED=0

for S in scan37 scan55 scan65; do
  D="$DR/$S"
  echo
  echo "############################################################"
  echo "### $S  $(date +%m-%d\ %H:%M)"
  echo "############################################################"

  # --- 阶段 A：完整三阶段，产出 geo/ref 检查点，同时即 w=0.01 基线 ---
  unset MGSR_ONLY_TOTAL MGSR_CKPT_DIR
  export MGSR_W_DEPTH=0.01
  echo "--- 完整跑（60k 步）w=0.01  $(date +%H:%M) ---"
  cd "$M"
  python -u train.py -s "$D" -m "$OUT/${S}_w001" -r 2 --eval > "$OUT/${S}_w001.log" 2>&1
  echo "    退出码 $?  $(date +%H:%M)"

  if [ ! -f "$OUT/${S}_w001/geo/chkpnt20000.pth" ]; then
    echo "!! $S 未产出检查点，跳过其余权重"
    continue
  fi

  # --- 阶段 B：复用检查点，只跑互导 20k 步 ---
  export MGSR_ONLY_TOTAL=1
  export MGSR_CKPT_DIR="$OUT/${S}_w001"
  for W in 0.1 0.5; do
    TAG="${S}_w$(echo "$W" | tr -d '.')"
    export MGSR_W_DEPTH=$W
    echo "--- 互导 20k 步  w=$W  $(date +%H:%M) ---"
    cd "$M"
    python -u train.py -s "$D" -m "$OUT/$TAG" -r 2 --eval > "$OUT/$TAG.log" 2>&1
    echo "    退出码 $?  $(date +%H:%M)"
  done
done

echo
echo "=== 跨场景轮结束 $(date +%m-%d\ %H:%M) ==="
