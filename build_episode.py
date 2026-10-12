"""单期拼接（在期目录里运行，目录内有 edl.py）：按 EDL 从 $SOURCES/<src>/faces2.mkv 切片（去 >0.3s 停顿、帧对齐），采样点精确拼音频，1.3x 变速。"""
import json, subprocess, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.getcwd())
SOURCES = os.environ.get('SOURCES', os.path.join(os.getcwd(), '..', 'sources'))
from durs import sil, refine
from edl import HOOK, CHAPTERS
FPS, SPEED, SR = 30, 1.3, 48000
phrases = [('hook', -1, s, p, t) for s, p, t in HOOK]
for ci, ch in enumerate(CHAPTERS):
    phrases += [('body', ci, s, p, t) for s, p, t in ch['segs']]
SIL = {}; PCM = {}
def pcm(src):
    if src not in PCM:
        fn = f'{SOURCES}/{src}/src.pcm'
        if not os.path.exists(fn):
            subprocess.run(['ffmpeg', '-v', 'error', '-i', f'{SOURCES}/{src}/faces2.mkv', '-map', '0:a', '-ac', '2', '-ar', '48000',
                            '-f', 's16le', fn, '-y'], check=True)
        PCM[src] = np.memmap(fn, dtype=np.int16, mode='r').reshape(-1, 2)
    return PCM[src]
os.makedirs('pieces', exist_ok=True)
lst = open('pieces/list.txt', 'w'); tl = []; t_src = 0.0; n = 0; audio = []; last = (None, -1)
for sec, ci, src, pieces, text in phrases:
    if src not in SIL: SIL[src] = sil(f'{SOURCES}/{src}/sil30.txt')
    p0 = t_src
    for a, b in [m for x, y in pieces for m in refine(x, y, SIL[src])]:
        if last[0] == src and last[1] - 1.0 < a < last[1]: a = last[1]          # 相邻片段重叠 → 截掉重叠部分
        if b - a < 2 / FPS: continue
        last = (src, b)
        nf = round((b - a) * FPS); d = nf / FPS; fn = f'pieces/{n:04d}.mkv'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a:.4f}', '-i', f'{SOURCES}/{src}/faces2.mkv', '-an',
                        '-frames:v', str(nf), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-r', '30', fn, '-y'], check=True)
        lst.write(f"file '{os.path.basename(fn)}'\n")
        i0 = round(a * SR); seg = pcm(src)[i0:i0 + nf * SR // FPS].astype(np.float32)
        fl = int(0.006 * SR); ramp = np.linspace(0, 1, fl)[:, None]; seg[:fl] *= ramp; seg[-fl:] *= ramp[::-1]
        audio.append(seg); n += 1; t_src += d
    tl.append(dict(sec=sec, ch=ci, text=text, t0=p0 / SPEED, t1=t_src / SPEED))
lst.close()
np.concatenate(audio).astype(np.int16).tofile('cat.pcm')
subprocess.run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', 'pieces/list.txt',
                '-f', 's16le', '-ar', '48000', '-ac', '2', '-i', 'cat.pcm',
                '-filter_complex', f'[0:v]setpts=PTS/{SPEED},fps=30[v];[1:a]atempo={SPEED}[a]',
                '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14',
                '-c:a', 'pcm_s16le', 'content.mkv', '-y'], check=True)
json.dump(tl, open('timeline.json', 'w'), ensure_ascii=False, indent=1)
print('pieces', n, 'source', round(t_src, 2), 'out', round(t_src / SPEED, 2))
