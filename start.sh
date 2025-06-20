#!/bin/bash
source /workspace/LivePortrait/liveportrait_env/bin/activate

echo "📦 framer rp_handle.py 실행 중..."

# torch 버전 확인
python -c "import torch; print(torch.__version__)"

# torchvision 버전 확인
python -c "import torchvision; print(torchvision.__version__)"

cd /workspace/LivePortrait
exec python -u rp_handle.py