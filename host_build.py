"""主持人独白素材：按 JSON 剪辑清单切片、去停顿、1.3x，输出 1000x580 的 hostA/hostB.mkv + 字幕时间轴 json。
用法: python3 host_build.py --video 独白.mov --edl host_edl.json --out host/ [--audio 原录音.mov] [--tonemap]
  host_edl.json: {"A": [[[[起,止], ...], "字幕"], ...], "B": [...]}   A=开场独白，B=结尾引流（可省略）
  --audio  画面和声音来自不同文件时用（例如画面用调好色的 SDR 导出版，声音用原录音；两者须同长、同步）
  --tonemap 画面是 iPhone HDR（HLG/PQ）时打开，做 HDR→SDR 色调映射，否则会发灰褪色"""
import json, subprocess, os, sys, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from durs import refine
ap = argparse.ArgumentParser(); ap.add_argument('--video', required=True); ap.add_argument('--edl', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--audio'); ap.add_argument('--tonemap', action='store_true'); ap.add_argument('--speed', type=float, default=1.3)
a = ap.parse_args()
a.video, a.edl = os.path.abspath(a.video), os.path.abspath(a.edl)
if a.audio: a.audio = os.path.abspath(a.audio)
os.makedirs(a.out, exist_ok=True); os.chdir(a.out)
FPS, SR = 30, 48000; EDL = json.load(open(a.edl))
w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', a.video],
                               capture_output=True, text=True).stdout.strip().strip(',').split(',')[:2])
cw = min(w, round(h * 1000 / 580)); vf = f'crop={cw}:{h}:{(w - cw) // 2}:0,scale=1000:580:flags=lanczos'
if a.tonemap: vf = 'zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,' + vf
inp = ['-i', a.video] + (['-i', a.audio, '-map', '0:v', '-map', '1:a'] if a.audio else [])
subprocess.run(['ffmpeg', '-v', 'error'] + inp + ['-vf', vf, '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14',
                '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', 'src.mkv', '-y'], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-i', 'src.mkv', '-f', 's16le', '-ar', '48000', '-ac', '2', 'src.pcm', '-y'], check=True)
r = subprocess.run(['ffmpeg', '-i', 'src.mkv', '-af', 'silencedetect=n=-36dB:d=0.3', '-vn', '-f', 'null', '-'], capture_output=True, text=True)
S = []; st = None
for l in r.stderr.splitlines():
    if 'silence_start' in l: st = float(l.split('silence_start:')[1])
    elif 'silence_end' in l and st is not None: S.append((st, float(l.split('silence_end:')[1].split('|')[0]))); st = None
pcm = np.memmap('src.pcm', dtype=np.int16, mode='r').reshape(-1, 2)
for part, rows in EDL.items():
    os.makedirs(f'p{part}', exist_ok=True); lst = open(f'p{part}/list.txt', 'w'); audio = []; tl = []; t = 0.0; n = 0
    for pieces, text in rows:
        p0 = t
        for x, y in [m for u, v in pieces for m in refine(u, v, S)]:
            nf = round((y - x) * FPS); fn = f'p{part}/{n:03d}.mkv'
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{x:.4f}', '-i', 'src.mkv', '-an', '-frames:v', str(nf), '-c:v', 'libx264',
                            '-preset', 'veryfast', '-crf', '14', '-r', '30', fn, '-y'], check=True)
            lst.write(f"file '{os.path.basename(fn)}'\n")
            i0 = round(x * SR); seg = pcm[i0:i0 + nf * SR // FPS].astype(np.float32)
            fl = int(0.006 * SR); ramp = np.linspace(0, 1, fl)[:, None]; seg[:fl] *= ramp; seg[-fl:] *= ramp[::-1]
            audio.append(seg); n += 1; t += nf / FPS
        tl.append(dict(text=text, t0=p0 / a.speed, t1=t / a.speed))
    lst.close(); np.concatenate(audio).astype(np.int16).tofile(f'cat{part}.pcm')
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', f'p{part}/list.txt', '-f', 's16le', '-ar', '48000', '-ac', '2',
                    '-i', f'cat{part}.pcm', '-filter_complex', f'[0:v]setpts=PTS/{a.speed},fps=30[v];[1:a]atempo={a.speed}[a]',
                    '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-c:a', 'pcm_s16le', f'host{part}.mkv', '-y'], check=True)
    json.dump(tl, open(f'host{part}.json', 'w'), ensure_ascii=False, indent=1)
    print(part, 'out', round(t / a.speed, 2))
