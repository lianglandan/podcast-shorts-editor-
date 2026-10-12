"""离线转写（sherpa-onnx + SenseVoice），输出 token 级时间戳。
用法: python3 asr_sensevoice.py <视频或音频> <tag> [--start 0] [--dur 全长]
产物: tok_<tag>.json = [(绝对秒, token), ...]，tok_<tag>.txt 便于浏览
要点: 先按静音切成 ≥12s 的小段；每次最多送 15 个文件，否则长批次会返回 0 token。"""
import subprocess, json, sys, os, re, argparse
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('tag')
ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--dur', type=float, default=None)
a = ap.parse_args()
MODELS = os.environ.get('MODELS', os.path.expanduser('~/.cache/podcast-shorts/models'))
BIN = f'{MODELS}/sherpa-onnx-v1.12.14-linux-x64-static/bin/sherpa-onnx-offline'
S = f'{MODELS}/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17'
if a.dur is None:
    a.dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.src], capture_output=True, text=True).stdout) - a.start
wav = f'{a.tag}.wav'
subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a.start), '-t', str(a.dur), '-i', a.src, '-vn', '-ac', '1', '-ar', '16000', wav, '-y'], check=True)
o = subprocess.run(['ffmpeg', '-i', wav, '-af', 'silencedetect=noise=-38dB:d=0.25', '-f', 'null', '-'], capture_output=True, text=True).stderr
sil = []; s = None
for k, v in re.findall(r'silence_(start|end): ([\d.]+)', o):
    v = float(v)
    if k == 'start': s = v
    elif s is not None: sil.append((s, v)); s = None
cuts = [0.0]
for x, y in sil:
    m = (x + y) / 2
    if m - cuts[-1] > 12: cuts.append(m)
cuts.append(a.dur); ch = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]
os.makedirs(f'c_{a.tag}', exist_ok=True); files = []
for i, (x, y) in enumerate(ch):
    fn = f'c_{a.tag}/{i:03d}.wav'; files.append(fn)
    subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(x), '-t', str(y - x), '-i', wav, fn, '-y'], check=True)
res = []
for b0 in range(0, len(files), 15):
    fb = files[b0:b0 + 15]
    out = subprocess.run([BIN, f'--sense-voice-model={S}/model.int8.onnx', f'--tokens={S}/tokens.txt', '--sense-voice-use-itn=1', '--num-threads=2'] + fb,
                         capture_output=True, text=True)
    cur = None
    for line in (out.stdout + out.stderr).splitlines():
        if line.startswith(f'c_{a.tag}/') and line.endswith('.wav'): cur = line
        elif line.startswith('{') and cur:
            j = json.loads(line); off = ch[files.index(cur)][0]
            res += [(round(a.start + off + t, 2), k) for k, t in zip(j['tokens'], j['timestamps'])]; cur = None
json.dump(res, open(f'tok_{a.tag}.json', 'w'), ensure_ascii=False)
print(a.tag, 'tokens', len(res))
