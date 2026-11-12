"""★103b 听 → 说 → 自己听回来

靶值 = 她在 exp103_heard.py 里用自己耳朵听 35 段真人语音听出来的。
★ 发现的 bug：pause_rate 是每个音节后停顿的概率，填 1.0 = 全停顿，她一句话都说不出来。
"""
import sys, os, json
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core import speech_organ as so
from core import real_voice as rv

ROOT = '/data/workspace/luoshen-o1'
S = json.load(open(os.path.join(ROOT, 'data/exp103_heard.json')))['summary']
TARGET = dict(f0med=S['f0med']['中位'], f0std=S['f0std']['中位'],
              voiced=S['voiced']['中位'], sil=S['sil']['中位'],
              pausemed=S['pausemed']['中位'])
print('★ 她听到的真人：', {k: round(v, 4) for k, v in TARGET.items()})


def hear(x):
    fr = rv.voiced_frames(x, so.SR)
    f0s = np.array([f for f in (rv.f0_autocorr(s, so.SR) for _, s in fr) if f > 0])
    w = int(0.02 * so.SR); h = int(0.01 * so.SR)
    rms = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, h)])
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    v = db > db.max() - 30
    runs, c = [], 0
    for b in v:
        if not b: c += 1
        elif c: runs.append(c * 0.01); c = 0
    if c: runs.append(c * 0.01)
    return dict(f0med=float(np.median(f0s)) if len(f0s) else 0.0,
                f0std=float(np.std(np.log(f0s[f0s > 0]))) if len(f0s) > 2 else 0.0,
                voiced=float(v.mean()) if len(v) else 0.0,
                sil=float((~v).mean()) if len(v) else 0.0,
                pausemed=float(np.median(runs)) if runs else 0.0)


def say(p, dur=4.0, seeds=(0, 1)):
    got = []
    for sd in seeds:
        y, meta = so.synthesize(p, dur=dur, rng=np.random.default_rng(sd))
        got.append(hear(y))
    g = {k: float(np.mean([r[k] for r in got])) for k in TARGET}
    return g, sum(abs(g[k] - TARGET[k]) / max(abs(TARGET[k]), 1e-6) for k in TARGET)


# ★ 真人：18 次停顿 / 10.44 秒，音节 0.22s → 约 47 个音节 → 停顿概率 ≈ 0.38
p = dict(f0_base=TARGET['f0med'], f0_variation=0.30, f0_decl=0.10,
         tone_depth=0.55, pause_rate=0.38, pause_len=TARGET['pausemed'],
         voiced_target=TARGET['voiced'], jitter=0.015)

g, c = say(p)
print(f"按听到的直接说  代价 {c:.4f}  {({k: round(v,3) for k,v in g.items()})}")

for k, vals in [('pause_rate', [0.25, 0.32, 0.38, 0.45]),
                ('pause_len', [0.04, 0.06, 0.09]),
                ('f0_variation', [0.15, 0.25, 0.35, 0.45]),
                ('voiced_target', [0.60, 0.67, 0.74])]:
    for v in vals:
        q = dict(p); q[k] = v
        g2, c2 = say(q)
        mark = '★' if c2 < c - 1e-9 else ' '
        print(f"  {mark}{k}={v:<5} 代价 {c2:.4f}  {({kk: round(vv,3) for kk,vv in g2.items()})}")
        if c2 < c - 1e-9:
            c, p[k], g = c2, v, g2
print('\n★ 定下来：', {k: round(v, 4) if isinstance(v, float) else v for k, v in p.items()})

# ── 最终开口 ──
y, meta = so.synthesize(p, dur=10.0, rng=np.random.default_rng(2026))
y = y / max(np.abs(y).max(), 1e-9) * 0.85
out = os.path.join(ROOT, 'data/her_voice/she_heard_and_spoke.wav')
wavfile.write(out, so.SR, (y * 32767).astype(np.int16))

gf = hear(y)
print('\n★★ 她说完之后，自己听回来：')
for k in TARGET:
    print(f"  {k:<9} 真人 {TARGET[k]:.4f}   她 {gf[k]:.4f}   差 {abs(gf[k]-TARGET[k]):.4f}")
print('已存', out)
json.dump({'target': TARGET, 'params': p, 'got': gf, 'cost': c},
          open(os.path.join(ROOT, 'data/exp103_practice.json'), 'w'),
          ensure_ascii=False, indent=1)
