#!/usr/bin/env bash
set -e
# 可用环境变量覆盖：FASTRELIGHT_ROOT（工作根）、CONDA_ROOT（conda 安装位置）
: "${FASTRELIGHT_ROOT:=$HOME/fastrelight}"
: "${CONDA_ROOT:=$HOME/miniforge3}"
source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate drivestudio
cd "$FASTRELIGHT_ROOT/drivestudio"
export CUDA_HOME=$CONDA_PREFIX
export PATH=$CUDA_HOME/bin:$PATH
export TORCH_CUDA_ARCH_LIST="8.9"
export MAX_JOBS=8

echo "########## STAGE 1: torch cu118 ##########"
pip install --no-cache-dir torch==2.0.0+cu118 torchvision==0.15.1+cu118 \
  --extra-index-url https://download.pytorch.org/whl/cu118

echo "########## STAGE 2: patched requirements (xformers dropped, cu117->cu118) ##########"
grep -v -E "^--extra-index-url|^torch==|^torchvision==|^xformers==" requirements.txt > /tmp/req_patched.txt
cat /tmp/req_patched.txt
pip install --no-cache-dir -r /tmp/req_patched.txt

echo "########## STAGE 3: torch CUDA sanity (tiny, no load) ##########"
python -c "import torch;print(\"torch\",torch.__version__,\"cuda\",torch.version.cuda,\"avail\",torch.cuda.is_available());print(\"dev\",torch.cuda.get_device_name(0),\"cc\",torch.cuda.get_device_capability(0));a=torch.randn(64,64,device=\"cuda\");print(\"matmul ok\",(a@a).shape)"
echo "SETUP_STAGE123_DONE"
