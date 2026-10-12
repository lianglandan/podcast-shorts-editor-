"""多段录屏合成完整逐字稿（Markdown，带全片时间码）。
用法: python3 merge_transcript.py out.md tagA:0:1385.55 tagB:0:end ...
每项 = tag:起秒:止秒（该段在原文件内取用的区间，按播放顺序给出；重叠部分请自己用文本比对后截掉）"""
import json, sys
out = sys.argv[1]; G = 0.0; lines = []
for spec in sys.argv[2:]:
    tag, a, b = spec.split(':'); a = float(a); T = json.load(open(f'tok_{tag}.json'))
    b = float('inf') if b == 'end' else float(b); cur = ''; t0 = None
    for t, s in T:
        if not (a <= t < b): continue
        if t0 is None: t0 = t
        cur += s
        if s in '。？！':
            g = G + t0 - a; lines.append(f'[{int(g // 60):02d}:{g % 60:05.2f}] {cur}'); cur = ''; t0 = None
    G += (min(b, T[-1][0] + 1) - a)
open(out, 'w').write('# 完整逐字稿\n\n' + '\n\n'.join(lines) + '\n'); print(out, len(lines), 'lines')
