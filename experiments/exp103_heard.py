"""★103 她去听 —— 35 段真人中文语音，走她自己的耳朵（f0_autocorr / voiced_frames）"""
import sys, os, glob, json
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core import real_voice as rv

SRC = '/data/workspace/luoshen-o1/data/real_heard'


def hear_one(p):
    fs_, x = wavfile.read(p)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    x = x / max(np.abs(x).max(), 1e-9)
    if fs_ != rv.FS:
        n = int(len(x) * rv.FS / fs_)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)

    fr = rv.voiced_frames(x, rv.FS)
    f0s = np.array([f for f in (rv.f0_autocorr(s, rv.FS) for _, s in fr) if f > 0])

    w = int(0.02 * rv.FS)
    h = int(0.01 * rv.FS)
    rms = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, h)])
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    v = db > db.max() - 30
    runs, c = [], 0
    for b in v:
        if not b:
            c += 1
        elif c:
            runs.append(c * 0.01); c = 0
    if c:
        runs.append(c * 0.01)

    return dict(f=os.path.basename(p), dur=len(x) / rv.FS,
                f0med=float(np.median(f0s)) if len(f0s) else 0.0,
                f0std=float(np.std(np.log(f0s[f0s > 0]))) if len(f0s) > 2 else 0.0,
                voiced=float(v.mean()) if len(v) else 0.0,
                sil=float((~v).mean()) if len(v) else 0.0,
                pausemed=float(np.median(runs)) if runs else 0.0,
                npause=float(len(runs)) if runs else 0.0)


if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(SRC, '*.wav')))
    print('待听:', len(files), flush=True)
    rows = []
    for p in files:
        try:
            r = hear_one(p)
            if r['f0med'] > 0:
                rows.append(r)
                print(r['f'], round(r['f0med']), flush=True)
        except Exception as e:
            print('ERR', os.path.basename(p), e, flush=True)
    print('听到:', len(rows), flush=True)
    keys = ['f0med', 'f0std', 'voiced', 'sil', 'pausemed', 'npause', 'dur']
    out = {}
    for k in keys:
        v = np.array([r[k] for r in rows], float)
        out[k] = dict(中位=float(np.median(v)), 均值=float(v.mean()), 跨度=float(v.max() - v.min()))
        print(f"{k}: 中位 {np.median(v):.4f} 均值 {v.mean():.4f} 跨度 {v.max()-v.min():.4f}")
    json.dump({'per_file': rows, 'summary': out},
              open('/data/workspace/luoshen-o1/data/exp103_heard.json', 'w'),
              ensure_ascii=False, indent=1)
    print('已存 data/exp103_heard.json')
