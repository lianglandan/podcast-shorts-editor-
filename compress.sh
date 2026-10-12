#!/usr/bin/env bash
# 2-pass 压到 ~29MB（聊天/传输工具单文件 30MB 上限时用）。用法: compress.sh in.mp4 out.mp4 [目标MB=29]
set -e; IN=$1; OUT=$2; MB=${3:-29}
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
B=$(python3 -c "print(min(4000, int($MB*8*1024/$D - 130)))")
ffmpeg -v error -i "$IN" -c:v libx264 -preset veryfast -b:v ${B}k -pass 1 -passlogfile /tmp/p2 -an -f null /dev/null -y
ffmpeg -v error -i "$IN" -c:v libx264 -preset veryfast -b:v ${B}k -pass 2 -passlogfile /tmp/p2 -c:a aac -b:a 128k -movflags +faststart "$OUT" -y
ls -la "$OUT"
