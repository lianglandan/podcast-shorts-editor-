"""SCRFD 人脸检测（insightface buffalo_sc 里的 det_500m.onnx），只返回最大分人脸。"""
import os, numpy as np, onnxruntime as ort, cv2
ort.set_default_logger_severity(3)
MODELS = os.environ.get('MODELS', os.path.expanduser('~/.cache/podcast-shorts/models'))
S = ort.InferenceSession(f'{MODELS}/det_500m.onnx', providers=['CPUExecutionProvider'])
IN = S.get_inputs()[0].name
def detect(img_bgr, size=320, thr=0.45):
    """返回最高分人脸 (cx, cy, w, h, score)，原图坐标；无则 None"""
    h, w = img_bgr.shape[:2]; sc = size / max(h, w)
    im = cv2.resize(img_bgr, (int(w * sc), int(h * sc))); pad = np.zeros((size, size, 3), np.uint8); pad[:im.shape[0], :im.shape[1]] = im
    blob = cv2.dnn.blobFromImage(pad, 1 / 128, (size, size), (127.5, 127.5, 127.5), swapRB=True)
    outs = S.run(None, {IN: blob}); best = None
    for k, st in enumerate((8, 16, 32)):
        sco = outs[k].reshape(-1); box = outs[k + 3].reshape(-1, 4) * st
        n = size // st; cy, cx = np.mgrid[:n, :n]; ctr = np.stack([cx, cy], -1).reshape(-1, 2) * st; ctr = np.repeat(ctr, 2, 0)
        i = int(sco.argmax())
        if sco[i] > thr and (best is None or sco[i] > best[4]):
            x0, y0 = ctr[i] - box[i, :2]; x1, y1 = ctr[i] + box[i, 2:]
            best = ((x0 + x1) / 2 / sc, (y0 + y1) / 2 / sc, (x1 - x0) / sc, (y1 - y0) / sc, float(sco[i]))
    return best
