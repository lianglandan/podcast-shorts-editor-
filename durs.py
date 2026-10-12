"""停顿压缩：片段内 >0.3s 的静音压成前后各 0.10s，并按 30fps 帧对齐。"""
FPS = 30; PAD, MAXGAP = 0.10, 0.30
def sil(path):
    out = []; st = None
    for l in open(path):
        k, v = l.split(); v = float(v)
        if k == 'start:': st = v
        elif st is not None: out.append((st, v)); st = None
    return out
def refine(a, b, S):
    q = lambda t: round(t * FPS) / FPS
    o = [[a, b]]
    for s, e in S:
        if e - s <= MAXGAP: continue
        n = []
        for x, y in o:
            if e <= x or s >= y: n.append([x, y]); continue
            if s > x: n.append([x, min(y, s + PAD)])
            if e < y: n.append([max(x, e - PAD), y])
        o = n
    return [(q(x), q(y)) for x, y in o if q(y) - q(x) >= 2 / FPS]
