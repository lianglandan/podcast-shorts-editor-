# podcast-shorts-editor

一个 Claude Skill：把长篇双人访谈 / 播客录屏，剪成抖音 3:4 竖屏口播短片。

- 离线转写（sherpa-onnx + SenseVoice，token 级时间戳）→ 完整逐字稿
- 拆分方案：多期短片 / 精华版 / 主题长片，含钩子、金句、敏感段落删除与衔接
- 5 秒钩子前置、1.3 倍速（不变音色）、自动压缩 >0.3s 停顿、帧级对齐、采样级音频拼接
- SCRFD 人脸跟踪，双人画框始终居中
- 「暖墨编辑部」排版：纸张肌理暖墨背景、单行衬线标题、等大双人画框、要点卡、一体化章节进度条、章节号水印、全片复盘卡
- 可选主持人开场独白（含 iPhone HDR → SDR 色调映射）

## 安装
把整个目录放进 Claude 的 skills 目录（如 `~/.claude/skills/podcast-shorts-editor/`），或在 Claude 设置里上传。

```bash
bash scripts/setup_models.sh   # 下载模型
sudo apt install ffmpeg fonts-noto-cjk fonts-noto-cjk-extra
```

## 目录
```
SKILL.md                 工作流与剪辑规则（Claude 读这个）
scripts/
  asr_sensevoice.py      转写，输出 tok_<tag>.json
  phrases.py             按短语打印时间与文本，写 EDL 用
  merge_transcript.py    多段录屏合成逐字稿
  track_faces.py         人脸跟踪裁出双人画框轨道 faces2.mkv + 静音表
  scrfd.py               SCRFD 人脸检测
  durs.py                停顿压缩与帧对齐
  build_episode.py       按 edl.py 拼接、变速 → content.mkv + timeline.json
  render_episode.py      排版合成 → final.mp4（可插主持人独白）
  layout_nuanmo.py       「暖墨编辑部」排版组件
  host_build.py          主持人独白切片（支持 --tonemap / --audio）
  host_solo.py           独白单独成片
  compress.sh            2-pass 压到 ~29MB
  setup_models.sh        下载模型
templates/               edl.py 模板、独白 EDL 模板、拆分方案模板
references/              敏感内容清单、排版规格、踩坑记录
```

## 许可
MIT
