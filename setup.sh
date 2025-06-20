#runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04
mkdir -p /workspace
cd /workspace

git clone https://github.com/KwaiVGI/LivePortrait
cd LivePortrait

python -m venv liveportrait_env
cd /workspace/LivePortrait
source /workspace/LivePortrait/liveportrait_env/bin/activate

# for CUDA 11.8
pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu118

pip install -r requirements.txt
pip install runpod

pip install -U "huggingface_hub[cli]"
huggingface-cli download KwaiVGI/LivePortrait --local-dir pretrained_weights --exclude "*.git*" "README.md" "docs"

apt update -y
apt install ffmpeg -y

#python inference.py -s ani1.jpeg -d ref.MOV
# source input is an image
# python inference.py -s assets/examples/source/s9.jpg -d assets/examples/driving/d0.mp4
# # source input is a video ✨
# python inference.py -s assets/examples/source/s13.mp4 -d assets/examples/driving/d0.mp4

#python action.py -s assets/examples/source/s9.jpg -d assets/examples/driving/d0.mp4 -o output/

#python action.py -s source.png -d driving.mov -o output/