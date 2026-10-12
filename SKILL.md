---
name: podcast-shorts-editor
description: 把长篇双人访谈/播客录屏（Zoom、腾讯会议、手机录屏）剪成抖音竖屏口播短片：转写逐字稿、出拆分方案、删敏感段落、5 秒钩子、1.3 倍速去停顿、人脸跟踪双人画框、「暖墨编辑部」排版逐期渲染。用户要剪访谈、拆分成多期、做精华版或长片时使用。
---

# 访谈 → 抖音口播短片

把一场 1–2 小时的双人访谈，按「先方案、再画面、后渲染」三道确认，剪成多期 3:4 竖屏短片。

## 固定剪辑规则（每期都遵守）
- **前 5 秒是钩子**：结论 + 冲突 + 金句。从正片中间挑最炸的一句挪到最前面；钩子播完再弹人物身份卡。
- **1.3 倍速**，只用 setpts + atempo，音色不变。
- **清除口误、重复和 >0.3 秒停顿**（停顿压到前后各 0.1s），衔接要自然，在完整句处断开。
- **画面人物居中**（人脸跟踪裁剪）。
- **字幕简体中文、单行、跟画面同步**；手动修正识别错字。
- **敏感内容删除**并说明衔接方式，清单见 `references/sensitive_checklist.md`。
- **每一步都要用户确认**：拆分方案 → 画面样板 → 渲染。不要跳过确认直接渲染。

## 环境
```bash
bash scripts/setup_models.sh          # sherpa-onnx + SenseVoice + SCRFD（只从 GitHub Releases 下载）
# 依赖：ffmpeg（含 zscale）、python3、numpy、pillow、scipy、opencv、onnxruntime、Noto CJK 字体
```
脚本都通过环境变量找资源：`MODELS`（模型目录）、`SOURCES`（素材轨道目录）、`FONT_DIR`（Noto 字体）。

## 流程

### 1. 收素材、转写、合成逐字稿
1. 先看每个文件：`ffprobe`（分辨率、时长、**是否 HDR**：color_transfer=arib-std-b67 → 需要色调映射）。截一帧看两人画面在哪。
2. 转写：`python3 scripts/asr_sensevoice.py 录屏1.mov v1`（每段一个 tag）。
3. 多段录屏要确定顺序和重叠：拿每段开头几句去其他段的转写里搜，找到重复句就截掉一份。
4. 合成完整逐字稿：`python3 scripts/merge_transcript.py 第N期_完整逐字稿.md v1:0:1385.55 v0:0:end ...`，交给用户。

### 2. 拆分方案（文档，等确认）
用 `templates/split_plan_template.md` 的结构写成文档（优先用协作文档；没有就 Markdown）：
- 素材概况 → 敏感段落表（全片时间 · 内容 · 原因 · 衔接）→ 方案 A（N 期短片）/ B（精华版 + 切片）/ C（3 期长片）→ 需要确认的事（方案、身份卡、栏目名、品牌名、争议期）。
- 每期列：主题、取用片段、**钩子原话**、**金句**、预估时长（原始时长 ÷ 1.3 × ~0.85）。
- 用 `python3 scripts/phrases.py tok_v1.json 起 止` 读原话、找时间点。钩子和金句只取原话，不编造。

### 3. 画面样板（图片，等确认）
- 用 `scripts/layout_nuanmo.py` 出 3 张：正文、章节卡、结尾复盘（规格见 `references/layout_spec.md`）。
- 用户改背景/配色只改 `P` 和 `background()`；改排版要防止和其他账号雷同。
- 身份卡文案、栏目名、结尾口号都放到样板里让用户一起确认。

### 4. 人脸跟踪画框轨道
```bash
python3 scripts/track_faces.py 录屏1.mov work/sources/v1 --left 576,95,427,771 --right 1493,98,307,168
```
`--left/--right` 是两人在原片里的像素区域（会议软件的小窗内缩 3px 去掉发言绿框）。先用 `--dur 20` 试跑，抽帧检查再跑全长。

### 5. 写剪辑清单并渲染
1. 每期一个目录，复制 `templates/edl_example.py` 为 `edl.py`，填 HOOK / CHAPTERS / META / INTRO。
   - 片段 = (素材名, [(起, 止), ...], 改正后的字幕)；跳过口误就拆成多段。
   - 品牌/人名不保留时：带名字的句子整句不要（声音里也不能出现）。
2. 渲染：
```bash
cd work/ep01
SOURCES=../sources python3 ../../scripts/build_episode.py
python3 ../../scripts/render_episode.py
bash ../../scripts/compress.sh final.mp4 out/第N期_01_标题.mp4      # 需要 ≤30MB 时
```
3. 抽 5–7 帧拼检查图：标题单行、字幕不溢出、引号不出框、进度条与章节对应、复盘卡完整。听一遍衔接处。
4. 多期可写成 shell 循环后台跑（`setsid nohup`），渲染完一期压缩一期。

### 6. 主持人独白（可选）
- 栏目介绍单独成片：`host_build.py` 切独白（HDR 加 `--tonemap`，或 `--audio` 用原录音配调好色的画面）→ `host_solo.py` 出片。
- 插进某一期：在该期 `edl.py` 加 `HOST = dict(dir=..., ...)`，钩子后放 A 段，复盘前放 B 段。只在用户要求的那一期加。
- 站外引流（小宇宙/公众号）放结尾，不放开头。

### 7. 交付
- 每期发给用户并写回用户指定的文件夹；一句话说明时长、钩子、做了哪些删除。
- 同一批素材做了多种剪法（短片 + 长片）时，提醒内容会重复，建议错开发布或分平台发。

## 参考
- `references/sensitive_checklist.md`：敏感内容类别与衔接原则
- `references/layout_spec.md`：「暖墨编辑部」排版规格
- `references/lessons.md`：HDR 褪色、音画漂移、ASR 批量、30MB 上限等坑
