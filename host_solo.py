"""主持人独白单独成片（栏目介绍视频）：hostA + hostB 连续，暖墨排版，无进度条。
用法: python3 host_solo.py <host_build 输出目录> <config.json> <out.mp4>
config.json: {"column": "...", "title_a": "...", "title_b": "...", "name": "主持人名", "role": "身份",
              "label": "栏目发起人", "cards": {"A": ["栏目介绍", "一句话"], "B": ["完整版", "平台"]}}"""
import json, subprocess, sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import layout_nuanmo as L
HD, CFG, OUT = sys.argv[1], json.load(open(sys.argv[2])), os.path.abspath(sys.argv[3])
FPS = 30; BG = L.background(); HBOX = (40, 262, 1040, 842)
HM = Image.new('L', (1000, 580), 0); ImageDraw.Draw(HM).rounded_rectangle((0, 0, 1000, 580), 26, fill=255)
parts = [p for p in 'AB' if os.path.exists(f'{HD}/host{p}.mkv')]
base = {}
for p in parts:
    img = BG.copy(); d = ImageDraw.Draw(img)
    L.header(d, CFG, -1, 1, '')
    img.paste(BG.crop((700, 70, 1050, 115)), (700, 70)); d = ImageDraw.Draw(img)
    L.track(d, (1040, 92), CFG.get('label', '栏目发起人'), L.sans(24, 'Medium'), L.P['gold'], sp=3, anchor='r')
    L.point_card(d, *CFG['cards'][p]); base[p] = img
ins = sum([['-i', f'{HD}/host{p}.mkv'] for p in parts], [])
afc = ''.join(f'[{i + 1}:a]' for i in range(len(parts))) + f'concat=n={len(parts)}:v=0:a=1[a]'
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{L.W}x{L.H}', '-r', '30', '-i', '-'] + ins +
                       ['-filter_complex', afc, '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT, '-y'], stdin=subprocess.PIPE)
for p in parts:
    tl = json.load(open(f'{HD}/host{p}.json'))
    hd = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', f'{HD}/host{p}.mkv', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    k = 0
    while True:
        b = hd.stdout.read(1000 * 580 * 3)
        if len(b) < 1000 * 580 * 3: break
        t = k / FPS; img = base[p].copy(); img.paste(Image.frombuffer('RGB', (1000, 580), b), HBOX[:2], HM); d = ImageDraw.Draw(img)
        d.rounded_rectangle(HBOX, 26, outline=L.P['panel_edge'], width=2)
        L.caption(d, HBOX, CFG['name'], CFG['role'], L.ease((t - 0.3) / 0.5) if p == 'A' else 1.0)
        for ph in tl:
            if ph['t0'] <= t < ph['t1']:
                ls = [x for x in re.split(r'(?<=，)', ph['text']) if x.strip('，')]; n = sum(len(l) for l in ls); tt = ph['t0']
                for l in ls:
                    dd = (ph['t1'] - ph['t0']) * len(l) / n
                    if tt <= t < tt + dd: L.subtitle(d, l.rstrip('，'))
                    tt += dd
        enc.stdin.write(img.tobytes()); k += 1
    hd.wait()
enc.stdin.close(); enc.wait(); print('done', OUT)
