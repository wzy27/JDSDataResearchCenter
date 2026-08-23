#!/usr/bin/env bash
set -e
# 可用环境变量覆盖：FASTRELIGHT_ROOT（工作根）、CONDA_ROOT（conda 安装位置）
: "${FASTRELIGHT_ROOT:=$HOME/fastrelight}"
: "${CONDA_ROOT:=$HOME/miniforge3}"
source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate drivestudio
cd "$FASTRELIGHT_ROOT/drivestudio"

conda install -y -c conda-forge gxx=11 gcc=11 2>&1 | tail -3

export CUDA_HOME=$CONDA_PREFIX
export PATH=$CUDA_HOME/bin:$PATH
export CC=$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-gcc
export CXX=$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-g++
export CUDAHOSTCXX=$CXX
export TORCH_CUDA_ARCH_LIST="8.9"
export MAX_JOBS=8
$CC --version | head -1

echo "########## gsplat 1.3.0 ##########"
pip install --no-cache-dir git+https://github.com/nerfstudio-project/gsplat.git@v1.3.0
echo "########## pytorch3d ##########"
pip install --no-cache-dir "git+https://github.com/facebookresearch/pytorch3d.git@stable"
echo "########## nvdiffrast ##########"
pip install --no-cache-dir git+https://github.com/NVlabs/nvdiffrast
echo "########## smplx (editable) ##########"
cd third_party/smplx && pip install -e . && cd ../..
echo "EXT_DONE"
