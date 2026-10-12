"""「暖墨编辑部」合成（在期目录里、build_episode.py 之后运行）：
钩子 → [主持人开场独白 A] → 章节卡 → 正文 … → [主持人结尾 B] → 全片复盘卡。
edl.py 需提供 CHAPTERS / META / INTRO；可选 HOST = dict(dir=..., name=..., role=..., label=..., cards={'A': (标签, 文案), 'B': (...)})
（HOST.dir 是 host_build.py 的输出目录，含 hostA/hostB.mkv 与 .json；不需要独白就不写 HOST）。"""
import json, re, subprocess, sys, os
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.getcwd())
import layout_nuanmo as L
import edl
from edl import CHAPTERS, META, INTRO
HOSTCFG = getattr(edl, 'HOST', None)

FPS = 30; T_CH, T_FINAL = 2.0, 6.0
FW, FH = 490, 580
meta = dict(column=META['column'], title_a=META['title_a'], title_b=META['title_b'])
if len(sys.argv) > 1: meta = json.loads(open(sys.argv[1]).read())   # 可外部指定
FINAL = dict(META['final'])
names = [c['bar'] for c in CHAPTERS]

tl = json.load(open('timeline.json'))
hook_end = max(p['t1'] for p in tl if p['sec'] == 'hook')
rng = [(min(p['t0'] for p in tl if p['ch'] == i), max(p['t1'] for p in tl if p['ch'] == i)) for i in range(len(CHAPTERS))]

# 字幕分行（无衬线 48，最宽 960）
_d = ImageDraw.Draw(Image.new('RGB', (8, 8))); _f = L.sans(48, 'Medium')
def tw(s): return _d.textlength(s, font=_f)
def split_lines(text, maxw=960):
    parts = [p.rstrip('，。') for p in text.replace('，', '，|').replace('？', '？|').split('|') if p.rstrip('，。')]
    out = []
    for p in parts:
        while tw(p) > maxw:
            toks = re.findall(r'[A-Za-z0-9%]+|.', p); best = None
            for k in range(1, len(toks)):
                a, b = ''.join(toks[:k]), ''.join(toks[k:])
                if tw(a) <= maxw:
                    sc = abs(tw(a) - tw(b)) - (60 if toks[k - 1] in '的了是吗呢说' else 0)
                    if best is None or sc < best[0]: best = (sc, k)
            k = best[1]; out.append(''.join(toks[:k])); p = ''.join(toks[k:])
        out.append(p)
    return out
subs = []
for ph in tl:
    ls = split_lines(ph['text']); n = sum(len(l) for l in ls); t = ph['t0']
    for l in ls:
        dd = (ph['t1'] - ph['t0']) * len(l) / n; subs.append((t, t + dd, l)); t += dd

BG = L.background()
_base = {}
def base(ci):
    if ci in _base: return _base[ci]
    img = BG.copy(); d = ImageDraw.Draw(img)
    L.header(d, meta, ci, len(CHAPTERS), CHAPTERS[ci]['name'] if ci >= 0 else '')
    if ci < 0: L.point_card(d, '本期看点', FINAL['gold'])
    else: L.point_card(d, f'本章要点 · {ci + 1:02d}', CHAPTERS[ci]['card'])
    _base[ci] = img; return img
MASK = Image.new('L', (FW, FH), 0); ImageDraw.Draw(MASK).rounded_rectangle((0, 0, FW, FH), 26, fill=255)

def content_frame(face, tc, ci, t_ch):
    img = base(ci).copy()
    img.paste(face.crop((0, 0, FW, FH)), L.JOY[:2], MASK)
    img.paste(face.crop((FW, 0, 2 * FW, FH)), L.DANA[:2], MASK)
    d = ImageDraw.Draw(img)
    for box in (L.JOY, L.DANA): d.rounded_rectangle(box, 26, outline=L.P['panel_edge'], width=2)
    for box, (nm, role, tin) in zip((L.JOY, L.DANA), INTRO):
        if ci < 0: L.caption(d, box, nm, '', 1.0)                              # 钩子期间只显示名字
        elif ci == 0: L.caption(d, box, nm, role, L.ease((t_ch - tin) / 0.5))
        else: L.caption(d, box, nm, role, 1.0)
    for a, b, s in subs:
        if a <= tc < b: L.subtitle(d, s); break
    if ci < 0: L.progress(d, names, -1, 0)
    else: L.progress(d, names, ci, (tc - rng[ci][0]) / max(1e-6, rng[ci][1] - rng[ci][0]))
    return img

HBOX = (40, 262, 1040, 842)
HM = Image.new('L', (1000, 580), 0); ImageDraw.Draw(HM).rounded_rectangle((0, 0, 1000, 580), 26, fill=255)
HOST = {p: json.load(open(f"{HOSTCFG['dir']}/host{p}.json")) for p in 'AB' if HOSTCFG and os.path.exists(f"{HOSTCFG['dir']}/host{p}.json")}
HCARD = HOSTCFG['cards'] if HOSTCFG else {}
_hb = {}
def host_base(p):
    if p in _hb: return _hb[p]
    img = BG.copy(); d = ImageDraw.Draw(img)
    L.header(d, meta, -1, len(CHAPTERS), '')
    img.paste(BG.crop((700, 70, 1050, 115)), (700, 70)); d = ImageDraw.Draw(img)
    L.track(d, (1040, 92), HOSTCFG.get('label', '栏目发起人'), L.sans(24, 'Medium'), L.P['gold'], sp=3, anchor='r')
    L.point_card(d, *HCARD[p]); _hb[p] = img; return img
def host_frame(p, fr, t):
    img = host_base(p).copy(); img.paste(fr, HBOX[:2], HM); d = ImageDraw.Draw(img)
    d.rounded_rectangle(HBOX, 26, outline=L.P['panel_edge'], width=2)
    L.caption(d, HBOX, HOSTCFG['name'], HOSTCFG['role'], L.ease((t - 0.3) / 0.5) if p == 'A' else 1.0)
    for ph in HOST[p]:
        if ph['t0'] <= t < ph['t1']:
            ls = split_lines(ph['text']); n = sum(len(l) for l in ls); tt = ph['t0']
            for l in ls:
                dd = (ph['t1'] - ph['t0']) * len(l) / n
                if tt <= t < tt + dd: L.subtitle(d, l)
                tt += dd
    if p == 'A': L.progress(d, names, -1, 0)
    else: L.progress(d, names, len(names), 0)
    return img

plan = [('content', 0.0, hook_end, -1)] + ([('host', 'A')] if 'A' in HOST else [])
for i in range(len(CHAPTERS)):
    plan += [('chapter', T_CH, i), ('content', rng[i][0], rng[i][1], i)]
plan += ([('host', 'B')] if 'B' in HOST else []) + [('final', T_FINAL, None)]

dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', 'content.mkv', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{L.W}x{L.H}', '-r', '30', '-i', '-',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', 'video_only.mp4', '-y'], stdin=subprocess.PIPE)
FS = 2 * FW * FH * 3; cidx = 0; last = None
def read_face():
    global cidx, last
    buf = dec.stdout.read(FS)
    if len(buf) == FS: last = Image.frombuffer('RGB', (2 * FW, FH), buf); cidx += 1
    return last
parts = []; nout = 0
for step in plan:
    if step[0] == 'host':
        p = step[1]; hd = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', f"{HOSTCFG['dir']}/host{p}.mkv", '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        k = 0
        while True:
            b = hd.stdout.read(1000 * 580 * 3)
            if len(b) < 1000 * 580 * 3: break
            enc.stdin.write(host_frame(p, Image.frombuffer('RGB', (1000, 580), b), k / FPS).tobytes()); k += 1; nout += 1
        hd.wait(); parts.append(('h', p, k / FPS)); print('host', p, nout, flush=True); continue
    if step[0] == 'content':
        _, c0, c1, ci = step; f0, f1 = round(c0 * FPS), round(c1 * FPS)
        while cidx < f0: read_face()
        for k in range(f0, f1):
            enc.stdin.write(content_frame(read_face(), k / FPS, ci, (k - f0) / FPS).tobytes()); nout += 1
        parts.append(('a', f0 / FPS, f1 / FPS))
    else:
        kind, dur, i = step; nf = round(dur * FPS)
        for k in range(nf):
            t = k / FPS
            im = (L.chapter_card(BG, CHAPTERS[i]['n'], CHAPTERS[i]['name'], CHAPTERS[i]['card'], t, names, i, 0.0)
                  if kind == 'chapter' else L.final_card(BG, FINAL, t, names))
            enc.stdin.write(im.tobytes()); nout += 1
        parts.append(('s', nf / FPS))
    print(step[0], nout, flush=True)
enc.stdin.close(); enc.wait(); dec.terminate()

fc, lab = [], []
for i, p in enumerate(parts):
    if p[0] == 'a': fc.append(f'[0:a]atrim={p[1]:.4f}:{p[2]:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={p[2]-p[1]-0.04:.4f}:d=0.04[a{i}]')
    elif p[0] == 'h': fc.append(f'[{2 + [q for q in "AB" if q in HOST].index(p[1])}:a]atrim=0:{p[2]:.4f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[a{i}]')
    else: fc.append(f'anullsrc=r=48000:cl=stereo,atrim=0:{p[1]:.4f}[a{i}]')
    lab.append(f'[a{i}]')
fc.append(''.join(lab) + f'concat=n={len(lab)}:v=0:a=1[aout]')
subprocess.run(['ffmpeg', '-v', 'error', '-i', 'content.mkv', '-i', 'video_only.mp4'] + sum([['-i', f"{HOSTCFG['dir']}/host{p}.mkv"] for p in 'AB' if p in HOST], []) + ['-filter_complex', ';'.join(fc),
                '-map', '1:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                '-movflags', '+faststart', 'final.mp4', '-y'], check=True)
print('done frames', nout, nout / FPS)
