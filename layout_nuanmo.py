"""「暖墨编辑部」排版：1080x1440（3:4）暖墨渐变 + 纸张肌理背景，杂志式衬线单行标题、两个等大人物画框、
要点卡（前后双引号）、与章节名一体的底部进度条、右上角超大半透明章节号水印、全片复盘卡。
字体：Noto Sans/Serif CJK（apt install fonts-noto-cjk fonts-noto-cjk-extra）。"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import os
FONT_DIR = os.environ.get('FONT_DIR', '/usr/share/fonts/opentype/noto')
W, H = 1080, 1440
_F = {}
def sans(size, w='Regular'):
    k = ('s', size, w)
    if k not in _F: _F[k] = ImageFont.truetype(f'{FONT_DIR}/NotoSansCJK-{w}.ttc', size, index=2)
    return _F[k]
def serif(size, w='Bold'):
    k = ('r', size, w)
    if k not in _F: _F[k] = ImageFont.truetype(f'{FONT_DIR}/NotoSerifCJK-{w}.ttc', size, index=2)
    return _F[k]

hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
P = dict(top=hx('#1C140B'), bot=hx('#2E2216'),          # 背景：比 A 方案更暖的琥珀墨
         gold=hx('#D9B77A'), gold_dim=hx('#7A6544'), ink=hx('#F3EDE3'), mute=hx('#A89A86'),
         faint=hx('#5E5244'), panel=hx('#241A11'), panel_edge=hx('#4A3C2B'))

def _blur_noise(rng, scale, shape):
    small = rng.normal(0, 1, (shape[0] // scale + 2, shape[1] // scale + 2)).astype(np.float32)
    im = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-6) * 255).astype(np.uint8))
    return np.asarray(im.resize((shape[1], shape[0]), Image.BICUBIC), np.float32) / 255 - 0.5

def background(seed=11):
    """v6 暖墨渐变 + 纸张肌理（斑驳、纤维横纹、细颗粒、边缘做旧）"""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
    top = np.array(P['top'], np.float32); bot = np.array(P['bot'], np.float32); t = y ** 1.15
    img = np.broadcast_to(top * (1 - t[..., None]) + bot * t[..., None], (H, W, 3)).copy()
    for cy, amp, sig in ((0.22, 9.0, 0.09), (0.70, 6.0, 0.10)):           # 横向琥珀柔光
        band = np.exp(-((y - cy) ** 2) / (2 * sig ** 2)) * (1 - 0.5 * x ** 2)
        img += band[..., None] * amp * np.array([1.0, 0.72, 0.40])
    tone = np.array([1.0, 0.80, 0.55], np.float32)
    img += (_blur_noise(rng, 180, (H, W)) * 14)[..., None] * tone      # 纸面大块斑驳
    img += (_blur_noise(rng, 36, (H, W)) * 6)[..., None] * tone        # 中尺度起伏
    fib = Image.fromarray(np.clip(rng.normal(128, 40, (H, W)), 0, 255).astype(np.uint8))
    fib = np.asarray(fib.resize((W // 6, H), Image.BILINEAR).resize((W, H), Image.BICUBIC), np.float32)
    img += ((fib - 128) / 40 * 3.0)[..., None] * tone                  # 纤维横纹
    img *= (1 - 0.14 * np.abs(x) ** 2)[..., None]                       # 左右暗角
    r = np.sqrt((x * 0.92) ** 2 + ((y - 0.5) * 2) ** 2)
    img *= (1 - np.clip(r - 0.8, 0, None) * 0.35)[..., None]            # 边缘做旧
    img += rng.normal(0, 2.4, (H, W, 1))                                # 细颗粒
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

def track(d, xy, s, font, fill, sp=4, anchor='l'):
    """字间距文本"""
    x, y = xy
    if anchor == 'c':
        tw = sum(d.textlength(c, font=font) for c in s) + sp * (len(s) - 1); x -= tw / 2
    elif anchor == 'r':
        tw = sum(d.textlength(c, font=font) for c in s) + sp * (len(s) - 1); x -= tw
    for c in s:
        d.text((x, y), c, font=font, fill=fill, anchor='lm'); x += d.textlength(c, font=font) + sp

def wrap(d, s, font, maxw):
    out, cur = [], ''
    for ch in s:
        if d.textlength(cur + ch, font=font) > maxw and cur: out.append(cur); cur = ch
        else: cur += ch
    out = out + ([cur] if cur else [])
    if len(out) > 1 and all(c in '，。？！、：；”）' for c in out[-1]):
        out[-2] += out[-1]; out.pop()
    return out

def lerp(a, b, k): return tuple(int(x + (y - x) * k) for x, y in zip(a, b))
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

# ---------- 公共元素 ----------
def header(d, meta, ch_idx, n_ch, ch_name):
    track(d, (40, 92), meta['column'], sans(24), P['mute'], sp=3)
    if ch_idx >= 0:
        s = f'{ch_idx + 1:02d} / {n_ch:02d}  ·  {ch_name}'
        track(d, (1040, 92), s, sans(24, 'Medium'), P['gold'], sp=2, anchor='r')
    else:
        track(d, (1040, 92), '本期看点', sans(24, 'Medium'), P['gold'], sp=3, anchor='r')
    f = serif(52); wa = d.textlength(meta['title_a'], font=f)
    if wa + d.textlength(meta['title_b'], font=f) > 960: f = serif(46); wa = d.textlength(meta['title_a'], font=f)
    d.text((40, 176), meta['title_a'], font=f, fill=P['ink'], anchor='lm')
    d.text((40 + wa, 176), meta['title_b'], font=f, fill=P['gold'], anchor='lm')
    d.line([(40, 226), (160, 226)], fill=P['gold'], width=3)

PROG_Y = 1300
def progress(d, names, cur, frac):
    """一体化章节进度条：每章一段，已讲满格、当前章按 frac 填充；章节名紧贴在各段下方"""
    n = len(names); x0, x1, gap = 40, 1040, 10; seg = (x1 - x0 - gap * (n - 1)) / n
    for i, s in enumerate(names):
        a = x0 + i * (seg + gap); b = a + seg
        d.rounded_rectangle((a, PROG_Y - 3, b, PROG_Y + 3), 3, fill=P['faint'])
        k = 1.0 if i < cur else (frac if i == cur else 0.0)
        if k > 0: d.rounded_rectangle((a, PROG_Y - 3, a + seg * k, PROG_Y + 3), 3, fill=P['gold'])
        col = P['gold'] if i == cur else (P['ink'] if i < cur else P['mute'])
        d.text(((a + b) / 2, PROG_Y + 32), s, font=sans(24, 'Medium' if i == cur else 'Regular'), fill=col, anchor='mm')

# 双人画框：两框等大 490x580
LEFT = (40, 262, 530, 842)
RIGHT = (550, 262, 1040, 842)
JOY, DANA = LEFT, RIGHT   # 兼容旧名
def fit(src, w, h):
    """居中裁成目标比例后缩放"""
    sw, sh = src.size; r = w / h
    if sw / sh > r: cw = int(sh * r); src = src.crop(((sw - cw) // 2, 0, (sw - cw) // 2 + cw, sh))
    else: ch = int(sw / r); src = src.crop((0, (sh - ch) // 2, sw, (sh - ch) // 2 + ch))
    return src.resize((w, h), Image.LANCZOS)
def frame(img, src, box, radius=26):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    im = fit(src, w, h)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w, h), radius, fill=255)
    img.paste(im, (x0, y0), m)
    ImageDraw.Draw(img).rounded_rectangle((x0, y0, x1, y1), radius, outline=P['panel_edge'], width=2)

def caption(d, box, name, role, k=1.0):
    """画框下方图注：名字常显，身份 role 按 k 从左滑入淡入"""
    x0, y1 = box[0], box[3] + 44
    d.rectangle((x0, y1 - 13, x0 + 4, y1 + 13), fill=P['gold'])
    d.text((x0 + 16, y1), name, font=serif(30), fill=P['ink'], anchor='lm')
    if role and k > 0:
        nw = d.textlength(name, font=serif(30)); dx = int((1 - k) * -20)
        d.text((x0 + 30 + nw + dx, y1), role, font=sans(24), fill=lerp(P['top'], P['mute'], k), anchor='lm')

def subtitle(d, s):
    d.text((W / 2, 966), s, font=sans(48, 'Medium'), fill=P['ink'], anchor='mm',
           stroke_width=2, stroke_fill=(20, 14, 8))

def point_card(d, label, text, k=1.0):
    """本章要点卡：衬线引号 + 一句话"""
    x0, y0, x1, y1 = 40, 1030, 1040, 1222
    d.rounded_rectangle((x0, y0, x1, y1), 22, fill=P['panel'], outline=P['panel_edge'], width=2)
    track(d, (x0 + 110, y0 + 46), label, sans(24, 'Medium'), P['gold'], sp=3)
    lines = wrap(d, text, serif(40, 'SemiBold'), 830)[:2]
    yy = y0 + 124 if len(lines) == 1 else y0 + 104
    d.text((x0 + 100, yy + 34), '“', font=serif(110), fill=P['gold_dim'], anchor='rm')
    for i, l in enumerate(lines):
        d.text((x0 + 110, yy + i * 60), l, font=serif(40, 'SemiBold'), fill=lerp(P['panel'], P['ink'], k), anchor='lm')
    lw = d.textlength(lines[-1], font=serif(40, 'SemiBold'))
    d.text((x0 + 110 + lw + 12, yy + (len(lines) - 1) * 60 + 34), '”', font=serif(110), fill=P['gold_dim'], anchor='lm')

# ---------- 全屏卡片 ----------
def chapter_card(bg, n, name, desc, t, names, cur, frac=0.0):
    """章节卡：超大衬线数字作背景水印，标题压在数字上"""
    img = bg.copy(); d = ImageDraw.Draw(img)
    progress(d, names, cur, frac)
    a0, a1, a2 = ease(t / 0.4), ease((t - 0.15) / 0.4), ease((t - 0.35) / 0.4)
    cy = 640
    wm = Image.new('RGBA', (W, H), (0, 0, 0, 0)); wd = ImageDraw.Draw(wm)
    sc = 0.92 + 0.08 * a0
    wd.text((1050, 40), n, font=serif(int(440 * sc), 'Black'), fill=P['gold'] + (int(60 * a0),), anchor='ra')
    img.paste(wm, (0, 0), wm); d = ImageDraw.Draw(img)
    d.text((W / 2, cy + int((1 - a1) * 24)), name, font=serif(84), fill=lerp(P['top'], P['ink'], a1), anchor='mm')
    lw = 160 * a1; d.line([(W / 2 - lw / 2, cy + 86), (W / 2 + lw / 2, cy + 86)], fill=P['gold'], width=3)
    for i, l in enumerate(wrap(d, desc, sans(32), 860)):
        d.text((W / 2, cy + 150 + i * 50), l, font=sans(32), fill=lerp(P['top'], P['mute'], a2), anchor='mm')
    return img

def final_card(bg, m, t, names):
    img = bg.copy(); d = ImageDraw.Draw(img)
    progress(d, names, len(names), 0.0)
    a0 = ease(t / 0.35)
    track(d, (60, 110), m['label'], sans(26, 'Medium'), lerp(P['top'], P['gold'], a0), sp=4)
    d.text((60, 182), m['title'], font=serif(54), fill=lerp(P['top'], P['ink'], a0), anchor='lm')
    d.line([(60, 234), (60 + 180 * ease(t / 0.6), 234)], fill=P['gold'], width=3)
    rows = m['rows']; n = len(rows); cols = 2; rws = (n + 1) // 2
    gw, gh, gx, gy = 470, min(200, 760 // rws - 20), 60, 276
    for i, (k, v) in enumerate(rows):
        a = ease((t - 0.4 - i * 0.25) / 0.35)
        if a <= 0: continue
        c, r = i % cols, i // cols
        x, y = gx + c * (gw + 20), gy + r * (gh + 20) + int((1 - a) * 16)
        d.rounded_rectangle((x, y, x + gw, y + gh), 20, fill=lerp(P['top'], P['panel'], a), outline=lerp(P['top'], P['panel_edge'], a), width=2)
        d.text((x + 30, y + 56), f'{i + 1:02d}', font=serif(54), fill=lerp(P['panel'], P['gold'], a), anchor='lm')
        d.text((x + 118, y + 56), k, font=serif(34), fill=lerp(P['panel'], P['ink'], a), anchor='lm')
        for j, l in enumerate(wrap(d, v, sans(26), gw - 60)[:3]):
            d.text((x + 30, y + 114 + j * 38), l, font=sans(26), fill=lerp(P['panel'], P['mute'], a), anchor='lm')
    a = ease((t - 0.4 - n * 0.25 - 0.1) / 0.4)
    ylast = gy + rws * (gh + 20) + 50
    for j, l in enumerate(wrap(d, m['gold'], serif(42), 960)):
        d.text((60, ylast + j * 60), l, font=serif(42), fill=lerp(P['top'], P['gold'], a), anchor='lm')
    d.text((60, ylast + 116), m['follow'], font=serif(34, 'SemiBold'), fill=lerp(P['top'], P['ink'], a), anchor='lm')
    return img
