"""把一段双人录屏（Zoom/腾讯会议）裁成两个 490x580 人脸跟踪画框，hstack 后带原音频输出 faces2.mkv，并生成静音表。
用法: python3 track_faces.py <录屏.mov> <输出目录> --left x,y,w,h --right x,y,w,h
  --left/--right 是两位说话人画面在原片中的像素区域（先用 ffmpeg 截一帧量好；会议软件的发言绿框请内缩 3px）。
  每 0.5s 检测一次人脸，中位数+滑动平均平滑后，通过 sendcmd 动态调整裁剪位置（窄高画面按纵向跟，扁宽画面按横向跟）。
HDR 素材（iPhone HLG，color_transfer=arib-std-b67）务必先转成 SDR，否则画面发灰褪色，见 references/lessons.md。"""
import sys, os, subprocess, argparse, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrfd import detect
from scipy.ndimage import median_filter, uniform_filter1d
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--left', required=True); ap.add_argument('--right', required=True)
ap.add_argument('--dur', type=float, default=None, help='只处理前 N 秒（试跑用）')
ap.add_argument('--fw', type=int, default=490); ap.add_argument('--fh', type=int, default=580)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
FW, FH, SR = a.fw, a.fh, 2.0
W0, H0 = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', a.src],
                                 capture_output=True, text=True).stdout.strip().strip(',').split(',')[:2])
tiles = []
for spec in (a.left, a.right):
    x, y, w, h = map(int, spec.split(','))
    if w / h < FW / FH: cw, ch, axis = w, round(w * FH / FW), 'y'      # 窄高 → 纵向跟踪
    else: cw, ch, axis = round(h * FW / FH), h, 'x'                    # 扁宽 → 横向跟踪
    tiles.append(dict(x=x, y=y, w=w, h=h, cw=cw, ch=ch, axis=axis, v=[]))
DUR = ['-t', str(a.dur)] if a.dur else []
p = subprocess.Popen(['ffmpeg', '-v', 'error'] + DUR + ['-i', a.src, '-vf', f'fps={SR}', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
FS = W0 * H0 * 3
while True:
    b = p.stdout.read(FS)
    if len(b) < FS: break
    g = np.frombuffer(b, np.uint8).reshape(H0, W0, 3)
    for t in tiles:
        f = detect(g[t['y']:t['y'] + t['h'], t['x']:t['x'] + t['w']])
        t['v'].append((f[1] if t['axis'] == 'y' else f[0]) if f else np.nan)
def smooth(v, default):
    v = np.array(v, float); i = np.arange(len(v)); ok = ~np.isnan(v)
    v = np.interp(i, i[ok], v[ok]) if ok.sum() else np.full(len(v), default)
    return uniform_filter1d(median_filter(v, 9), 10)
for t in tiles:
    if t['axis'] == 'y': t['off'] = np.clip(smooth(t['v'], t['h'] / 2) - t['ch'] * 0.42, 0, t['h'] - t['ch']).round().astype(int)   # 脸放在框上 42%
    else: t['off'] = np.clip(smooth(t['v'], t['w'] / 2) - t['cw'] / 2, 0, t['w'] - t['cw']).round().astype(int)
with open(f'{a.out}/cmds.txt', 'w') as fh:
    for i in range(len(tiles[0]['off'])):
        fh.write(f"{i / SR:.2f} crop@c0 {tiles[0]['axis']} {tiles[0]['off'][i]}, crop@c1 {tiles[1]['axis']} {tiles[1]['off'][i]};\n")
parts = [f"[0:v]sendcmd=f={a.out}/cmds.txt,split[a][b]"]
for k, (t, lab) in enumerate(zip(tiles, 'ab')):
    ox, oy = (0, t['off'][0]) if t['axis'] == 'y' else (t['off'][0], 0)
    sharpen = ',unsharp=5:5:0.9' if t['ch'] < FH else ''          # 小窗放大后补一点锐度
    parts.append(f"[{lab}]crop={t['w']}:{t['h']}:{t['x']}:{t['y']},crop@c{k}={t['cw']}:{t['ch']}:{ox}:{oy},scale={FW}:{FH}:flags=lanczos{sharpen}[t{k}]")
parts.append('[t0][t1]hstack[v]'); fc = ';'.join(parts)
subprocess.run(['ffmpeg', '-v', 'error'] + DUR + ['-i', a.src, '-filter_complex', fc, '-map', '[v]', '-map', '0:a', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast',
                '-crf', '15', '-c:a', 'pcm_s16le', '-ar', '48000', f'{a.out}/faces2.mkv', '-y'], check=True)
r = subprocess.run(['ffmpeg', '-i', f'{a.out}/faces2.mkv', '-af', 'silencedetect=n=-36dB:d=0.3', '-vn', '-f', 'null', '-'], capture_output=True, text=True)
with open(f'{a.out}/sil30.txt', 'w') as fh:
    for l in r.stderr.splitlines():
        if 'silence_start' in l: fh.write('start: ' + l.split('silence_start:')[1].strip() + '\n')
        elif 'silence_end' in l: fh.write('end: ' + l.split('silence_end:')[1].split('|')[0].strip() + '\n')
print('done', a.out)
