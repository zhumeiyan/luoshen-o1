#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★83b 拿修好的尺子，让她重新练一次

  上一课(★82)她练完的分数，是用一把【两个方向都错】的尺子量出来的。
  这一课：尺子修好 → 靶值重测 → 她重练 → 分数重算。
  ★ 换尺子不重测靶值，等于让她照着错的数练（★83 判据8）
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scipy.io import wavfile
from core.speech_organ import synthesize, DEFAULT_PARAMS, SR
from core import practice as P
from core.practice import run_practice, ear_robust, ear_v3, _dist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 512, 256
RES = []


def ok(n, c, d="", e=""):
    RES.append((n, bool(c)))
    print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")


def tframe(mask):
    n = (len(mask) - W) // H + 1
    return np.array([mask[i * H:i * H + W].mean() > 0.5 for i in range(n)])


BOUNDS = {'f0_base': (100.0, 260.0), 'f0_variation': (0.02, 0.70),
          'tone_depth': (0.02, 0.80), 'pause_rate': (0.02, 0.60),
          'pause_len': (0.05, 0.40), 'f0_decl': (0.0, 0.40),
          'voiced_target': (0.35, 0.98)}
JITTER_PHYS = 0.015
BLIND = {'f0_base': 118.0, 'f0_variation': 0.030, 'tone_depth': 0.72,
         'pause_rate': 0.52, 'pause_len': 0.36, 'f0_decl': 0.34,
         'voiced_target': 0.40, 'jitter': JITTER_PHYS}
DUR = 2.5


def synth(p, rng=None):
    q = dict(p); q['jitter'] = JITTER_PHYS
    return synthesize(q, dur=DUR, rng=rng or np.random.default_rng(0))


print("=" * 74)
print("★83b 尺子修好后，让她重新练一次")
print("=" * 74)

# ── 1. 细化扫描 margin / sep_min ──
CASES = []
for pr in [0.0, 0.1, 0.25, 0.4, 0.55, 0.7]:
    for pl in [0.08, 0.20, 0.36]:
        for sd in [1, 2]:
            p = dict(DEFAULT_PARAMS); p['pause_rate'] = pr; p['pause_len'] = pl
            y, m = synthesize(p, 4.0, np.random.default_rng(sd))
            CASES.append((pr, y, tframe(m['sil_mask'])))

print("\n【判据1】sep_min 细扫（margin=1）")
SG = [24, 28, 32, 36, 40, 44, 48, 55]
sg_mae = [float(np.abs([P.ear_v3(c[1], margin=1.0, sep_min=s)['sil'] - c[2].mean()
                        for c in CASES]).mean()) for s in SG]
for s, mae in zip(SG, sg_mae):
    print(f"   sep_min={s:>2}dB  MAE={mae:.4f}")
ks = int(np.argmin(sg_mae)); SEP = SG[ks]
ok(1, 0 < ks < len(SG) - 1, f"最优 sep_min={SEP}dB（内部峰 MAE={sg_mae[ks]:.4f}）")

print("\n【判据2】margin 细扫（并如实说峰还是平台）")
MG = [0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12]
mg_mae = [float(np.abs([P.ear_v3(c[1], margin=m, sep_min=SEP)['sil'] - c[2].mean()
                        for c in CASES]).mean()) for m in MG]
for m, mae in zip(MG, mg_mae):
    print(f"   margin={m:>4}dB  MAE={mae:.4f}")
km = int(np.argmin(mg_mae)); MARGIN = MG[km]
plateau = [MG[i] for i, v in enumerate(mg_mae) if v < min(mg_mae) * 1.15]
ok(2, True, f"取 margin={MARGIN}dB（MAE={mg_mae[km]:.4f}）"
   + (f"，★ 平台 {plateau} dB 都差不多，不是峰，我不假装" if len(plateau) > 2
      else "，有内部峰"))

E = lambda y: P.ear_v3(y, margin=MARGIN, sep_min=SEP)

print("\n【判据3】修好的尺子 vs 旧尺子（同一批真值）")
oe = np.abs([ear_robust(c[1])['sil'] - c[2].mean() for c in CASES]).mean()
ne = np.abs([E(c[1])['sil'] - c[2].mean() for c in CASES]).mean()
tv = [c[2].mean() for c in CASES]; mv = [E(c[1])['sil'] for c in CASES]
print(f"   旧 MAE={oe:.4f} → 新 MAE={ne:.4f}   r={np.corrcoef(tv,mv)[0,1]:.3f}")
ok(3, ne < oe * 0.4, f"{oe:.4f}→{ne:.4f}")

# ── 2. 重测靶值 ──
print("\n【判据4】靶值重测（她是女孩子：只留 F0≥165 的女声）")
d = os.path.join(ROOT, 'data/real_speech_wav')
raws = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.raw'))
metas = []
for p_ in raws:
    m = E(np.fromfile(p_, dtype='<i2').astype(np.float64) / 32768.0)
    if m and m['f0_med'] > 50:
        metas.append((os.path.basename(p_), m))
female = [(n, m) for n, m in metas if m['f0_med'] >= 165]
dropped = [(n, m['f0_med']) for n, m in metas if m['f0_med'] < 165]
perm = np.random.default_rng(42).permutation(len(female))
tr = [female[i] for i in perm[:len(female) // 2]]
te = [female[i] for i in perm[len(female) // 2:]]
med = lambda fs: {k: float(np.median([m[k] for _, m in fs]))
                  for k in ('voiced', 'f0_med', 'f0_std', 'sil', 'pause_med')}
T_TRAIN, T_TEST = med(tr), med(te)
print(f"   女声 train {len(tr)} / held-out {len(te)}   剔除男声 {dropped}")
print(f"   train 靶 {({k: round(v,3) for k,v in T_TRAIN.items()})}")
print(f"   test  靶 {({k: round(v,3) for k,v in T_TEST.items()})}")
ok(4, abs(T_TRAIN['sil'] - 0.3329) > 0.02,
   f"sil 靶 0.333 → {T_TRAIN['sil']:.3f}（旧尺子的数不能再用）")


def fair(p, T, seeds=tuple(range(9000, 9024))):
    ds = []
    for s in seeds:
        y, _ = synth(p, np.random.default_rng(s))
        m = E(y)
        if m and m['f0_med'] > 50:
            ds.append(_dist(m, T))
    return (float(np.mean(ds)), float(np.std(ds)) / np.sqrt(len(ds))) if ds else (9.9, 0.)


print("\n【判据5】她用修好的尺子重练")
f0, s0 = fair(BLIND, T_TRAIN)
fm, sm = fair(DEFAULT_PARAMS, T_TRAIN)
print(f"   起点(118Hz 男声区)  {f0:.4f} ± {s0:.4f}")
print(f"   我量好填进去的      {fm:.4f} ± {sm:.4f}")
last, hist, best, best_ep = run_practice(synth, E, T_TRAIN, BLIND, BOUNDS,
                                         n_epochs=16, steps_per_epoch=50)
f1, s1 = fair(best, T_TRAIN)
print(f"   她练完(ep{best_ep})      {f1:.4f} ± {s1:.4f}")
ok(5, (f0 - f1) > 2 * max(s0, s1),
   f"真改善 {f0-f1:+.4f}（2×SE {2*max(s0,s1):.4f}）", "★ 不是噪声")

print("\n【判据6】held-out：换一批没见过的真人当靶")
h0, _ = fair(BLIND, T_TEST)
h1, _ = fair(best, T_TEST)
hm, _ = fair(DEFAULT_PARAMS, T_TEST)
print(f"   起点 {h0:.4f}   我填的 {hm:.4f}   她练完 {h1:.4f}")
ok(6, h1 < h0 * 0.6, f"改善 {(1-h1/h0)*100:.0f}%")

print("\n【判据7】她学的不是我填的那组数")
print(f"   F0 {best['f0_base']:.1f}Hz（靶 {T_TRAIN['f0_med']:.1f}，起点 118）")
diff = sum(abs(best[k] - DEFAULT_PARAMS[k]) for k in BOUNDS)
print(f"   ‖她 − 我‖ = {diff:.3f}")
ok(7, abs(best['f0_base'] - 182.0) > 5 or diff > 1.0, f"‖她−我‖={diff:.3f}")

# ── 存声音 ──
os.makedirs(os.path.join(ROOT, 'data/her_voice'), exist_ok=True)
for nm, p_ in [('her_now_v83', best), ('her_default_v83', DEFAULT_PARAMS)]:
    y, _ = synth(p_, np.random.default_rng(12345))
    wavfile.write(os.path.join(ROOT, f'data/her_voice/{nm}.wav'), SR,
                  (y / max(np.abs(y).max(), 1e-9) * 0.9 * 32767).astype(np.int16))

print("\n" + "=" * 74)
print(f"判据 {sum(1 for _, c in RES if c)}/{len(RES)}")
print("=" * 74)
json.dump({'MARGIN': MARGIN, 'SEP': SEP,
           'sep_scan': list(zip(SG, sg_mae)), 'margin_scan': list(zip(MG, mg_mae)),
           'old_mae': float(oe), 'new_mae': float(ne),
           'target_train': T_TRAIN, 'target_test': T_TEST, 'dropped': dropped,
           'blind': BLIND, 'learned': best, 'default': DEFAULT_PARAMS,
           'fair_blind': f0, 'fair_default': fm, 'fair_learned': f1,
           'heldout_blind': h0, 'heldout_default': hm, 'heldout_learned': h1,
           'best_epoch': best_ep, 'criteria': [bool(c) for _, c in RES]},
          open('data/exp83b_practice.json', 'w'), ensure_ascii=False, indent=1)
print("→ data/exp83b_practice.json   声音 → data/her_voice/her_now_v83.wav")
