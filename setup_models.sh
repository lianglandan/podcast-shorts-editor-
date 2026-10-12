#!/usr/bin/env bash
# 下载离线模型（只用 GitHub Releases）：sherpa-onnx 静态二进制、SenseVoice 中文 ASR、insightface SCRFD 人脸检测。
set -e
MODELS=${MODELS:-$HOME/.cache/podcast-shorts/models}; mkdir -p "$MODELS"; cd "$MODELS"
R=https://github.com/k2-fsa/sherpa-onnx/releases/download
[ -d sherpa-onnx-v1.12.14-linux-x64-static ] || { curl -sSLO $R/v1.12.14/sherpa-onnx-v1.12.14-linux-x64-static.tar.bz2 && tar xjf sherpa-onnx-v1.12.14-linux-x64-static.tar.bz2; }
[ -d sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 ] || { curl -sSLO $R/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2 && tar xjf sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2; }
[ -f det_500m.onnx ] || { curl -sSLO https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip && unzip -o buffalo_sc.zip det_500m.onnx; }
pip install --quiet onnxruntime opencv-python-headless scipy numpy pillow 2>/dev/null || pip install --quiet --break-system-packages onnxruntime opencv-python-headless scipy numpy pillow
echo "models ready in $MODELS"
