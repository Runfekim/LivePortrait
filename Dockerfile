FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

WORKDIR /workspace
RUN apt update && apt install -y bash

WORKDIR /workspace/LivePortrait
COPY action.py .
COPY rp_handle.py .

WORKDIR /workspace
COPY setup.sh .
RUN chmod +x setup.sh
RUN ./setup.sh

WORKDIR /workspace/LivePortrait
COPY start.sh .
RUN chmod +x start.sh

CMD ["/bin/bash", "-c", "/workspace/LivePortrait/start.sh"]
