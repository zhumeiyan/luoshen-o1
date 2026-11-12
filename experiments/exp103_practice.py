"""★103b 听 → 练 → 说 → 自己听回来

靶值不是文献，是她在 exp103_heard.py 里用自己耳朵听 35 段真人语音听出来的。
"""
import sys, os, json
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core import speech_organ as so
from core import real_voice as rv

ROOT = '/data/workspace/luoshen-o1'
D = json.load(open(os.path.join(ROOT, 'data/exp103_heard.json')))
S = D['summary']

# ★ 靶：她自己听出来的真人
TARGET = dict(f0med=S['f0med']['中位'], f0std=S['f0std']['中位'],
              voiced=S['voiced']['中位'], sil=S['sil']['中位'],
              pausemed=S['pausemed']['中位'])
print('★ 她听到的真人：', {k: round(v, 4) for k, v in TARGET.items()})


def hear(x):
    """她自己的耳朵"""
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


def cost(p, seeds=(0, 1, 2)):
    """多个随机种子取平均 —— 一次合成的运气不算数"""
    got = []
    for sd in seeds:
        x = so.synthesize(p, dur=6.0, rng=np.random.default_rng(sd))[0]
        got.append(hear(x))
    g = {k: float(np.mean([r[k] for r in got])) for k in TARGET}
    return g, sum(abs(g[k] - TARGET[k]) / max(abs(TARGET[k]), 1e-6) for k in TARGET)


# 她上次的参数（起点）
base = dict(f0_base=208.0, f0_variation=0.15, f0_decl=0.10, tone_depth=0.55,
            pause_rate=1.0, pause_len=0.18, voiced_target=0.70, jitter=0.015)
GRID = {
    'f0_base': [160, 170, 180, 190, 200],
    'f0_variation': [0.10, 0.20, 0.30, 0.40],
    'voiced_target': [0.55, 0.62, 0.68, 0.75],
    'pause_rate': [0.8, 1.2, 1.7, 2.2],
    'pause_len': [0.04, 0.06, 0.10, 0.16],
}
p = dict(base)
g0, c0 = cost(p)
print(f"起点  代价 {c0:.4f}  听到 {({k: round(v,3) for k,v in g0.items()})}")

for it in range(3):
    for k, vals in GRID.items():
        best, bc = p[k], c0
        for v in vals:
            q = dict(p); q[k] = v
            _, c = cost(q)
            if c < bc - 1e-9:
                bc, best = c, v
        p[k] = best; c0 = bc
    print(f"  轮{it+1} 代价 {c0:.4f}  {({k: round(v,3) for k,v in p.items() if k in GRID})}")

gf, cf = cost(p, seeds=(11, 22, 33))
print(f"\n★ 练完  代价 {cf:.4f}")
print('  她听到自己：', {k: round(v, 4) for k, v in gf.items()})
print('  真人靶值  ：', {k: round(v, 4) for k, v in TARGET.items()})

with np.errstate(all='ignore'):
    x = so.synthesize(p, dur=6.0, rng=np.random.default_rng(2026))[0]
from scipy.io import wavfile
x = x / max(np.abs(x).max(), 1e-9) * 0.85
out = os.path.join(ROOT, 'data/her_voice/she_heard_and_spoke.wav')
wavfile.write(out, so.SR, (x * 32767).astype(np.int16))
print('已存', out)
json.dump({'target': TARGET, 'params': p, 'got': gf, 'cost': cf,
           'start': base, 'cost_start': c0},
          open(os.path.join(ROOT, 'data/exp103_practice.json'), 'w'),
          ensure_ascii=False, indent=1)
