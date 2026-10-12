"""把 token 时间戳聚成短语，打印 起点 终点 文本，用于写剪辑清单（EDL）。
用法: python3 phrases.py tok_<tag>.json <起秒> <止秒>"""
import json, sys
T = json.load(open(sys.argv[1])); a, b = float(sys.argv[2]), float(sys.argv[3])
cur, out = [], []
for t, s in T:
    if cur and t - cur[-1][0] > 0.45: out.append(cur); cur = []
    cur.append((t, s))
    if s in '，。？！,.?!': out.append(cur); cur = []
if cur: out.append(cur)
for p in out:
    t0, t1 = p[0][0], p[-1][0]
    if t1 >= a and t0 <= b: print(f'{t0:8.2f} {t1 + 0.2:8.2f} ' + ''.join(s for _, s in p))
