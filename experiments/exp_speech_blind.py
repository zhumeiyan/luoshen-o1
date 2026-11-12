#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★81b 说话 —— 从【瞎的】起点学（真正的"学回来"）

════ 为什么要有这一课 ════
  ★81 主实验的判据1 说"改善 29%"，但用 128 句全新句子复核后发现：
      我填的默认  0.2657 ± 0.0106
      搜索学到的  0.2681 ± 0.0099     差 −0.0023（在噪声里）

  ★ 根因：我的默认参数本来就是用真人录音量出来的
      f0_base=182（真人中位 181.8）
      f0_variation=0.31（真人 0.331）
      pause_len=0.13（真人 0.144）
      voiced_target=0.79（真人 0.778）
   我已经替她把答案填好了 —— 她没有可学的空间，
   "学到的改善"其实是她在拟合挑选时用的那 3 个随机种子。

════ 这一课的做法 ════
  给她一个【瞎的】起点（全错），让她自己爬到真人统计。
  并且：挑选用种子 A，打分用没参与挑选的 64 句全新种子。

════ 结果 ════
  瞎起点  公平分 1.2661 ± 0.0274
  学完    公平分 0.2386 ± 0.0113     改善 81%（远超 2×标准误 0.0549）
  而且比"我量好填进去的"默认（0.2657）更好。
"""

from __future__ import annotations
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from speech_organ import synthesize, DEFAULT_PARAMS, SR  # noqa


def frame_sig(x, w=512, h=256):
    n = (len(x) - w) // h + 1
    return np.stack([x[i * h:i * h + w] for i in range(n)]) if n > 0 else np.zeros((0, w))


def ear(x):
    F = frame_sig(x)
    if len(F) < 10:
        return None
    rms = np.sqrt((F ** 2).mean(1))

    def f0_of(seg):
        s = seg - seg.mean()
        if np.sqrt((s ** 2).mean()) < 1e-5:
            return 0.0
        c = np.correlate(s, s, 'full')[len(s) - 1:]
        if c[0] <= 0:
            return 0.0
        c = c / c[0]
        lo, hi = int(SR / 500), min(int(SR / 70), len(c) - 1)
        reg = c[lo:hi]
        return SR / (int(np.argmax(reg)) + lo) if len(reg) else 0.0

    f0s = np.array([f0_of(f) for f in F])
    v = f0s > 20
    vf = f0s[v]
    thr = np.median(rms) * 0.25
    sil = rms < thr
    d = np.diff(np.concatenate([[0], sil.astype(int), [0]]))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    pl = [(e - s) * 256 / SR for s, e in zip(st, en) if (e - s) * 256 / SR > 0.05]
    return {'voiced': float(v.mean()),
            'f0_med': float(np.median(vf)) if len(vf) > 5 else 0.0,
            'f0_std': float(np.std(np.log(vf))) if len(vf) > 5 else 0.0,
            'sil': float(sil.mean()),
            'pause_med': float(np.median(pl)) if pl else 0.0}


SCALE = {'voiced': 0.30, 'f0_med': 60.0, 'f0_std': 0.20, 'sil': 0.20, 'pause_med': 0.20}


def dist(a, b):
    return float(np.mean([abs(a[k] - b[k]) / SCALE[k] for k in SCALE]))


BOUNDS = {
    'f0_base': (100.0, 260.0), 'f0_variation': (0.02, 0.70),
    'tone_depth': (0.02, 0.80), 'pause_rate': (0.02, 0.60),
    'pause_len': (0.05, 0.40), 'f0_decl': (0.0, 0.40),
    'voiced_target': (0.35, 0.98), 'jitter': (0.0, 0.12),
}

# ★ 瞎起点：全错，不是我量好的
BLIND = {'f0_base': 118.0, 'f0_variation': 0.030, 'tone_depth': 0.72,
         'pause_rate': 0.52, 'pause_len': 0.36, 'f0_decl': 0.34,
         'voiced_target': 0.40, 'jitter': 0.10}

PICK = (1, 2, 3)                       # 挑选用的种子
FAIR = tuple(range(9000, 9064))        # 打分用的 64 句全新种子（没参与挑选）


def main():
    raws = sorted([os.path.join('data/real_speech_wav', f)
                   for f in os.listdir('data/real_speech_wav') if f.endswith('.raw')])
    rng0 = np.random.default_rng(42)
    perm = rng0.permutation(len(raws))
    train = [raws[i] for i in perm[:len(raws) // 2]]
    test = [raws[i] for i in perm[len(raws) // 2:]]

    def targets(files):
        fs = []
        for p in files:
            m = ear(np.fromfile(p, dtype='<i2').astype(np.float64) / 32768.0)
            if m and m['f0_med'] > 50:
                fs.append(m)
        return {k: float(np.median([f[k] for f in fs])) for k in fs[0]}

    T_train = targets(train)
    T_test = targets(test)

    def fair(p, T=T_train):
        ds = []
        for s in FAIR:
            y, _ = synthesize(p, dur=2.5, rng=np.random.default_rng(s))
            m = ear(y)
            if m and m['f0_med'] > 50:
                ds.append(dist(m, T))
        return float(np.mean(ds)), float(np.std(ds)) / np.sqrt(max(len(ds), 1))

    def ev(p, T=T_train, seeds=PICK):
        ds = []
        for s in seeds:
            y, _ = synthesize(p, dur=2.5, rng=np.random.default_rng(s))
            m = ear(y)
            ds.append(dist(m, T) if (m and m['f0_med'] > 50) else 9.9)
        return float(np.mean(ds))

    print("=" * 74)
    print("★81b 说话 —— 从【瞎的】起点学回来")
    print("=" * 74)
    print(f"  训练集 {len(train)} 段真人 → 目标 {({k: round(v,3) for k,v in T_train.items()})}")

    f0, s0 = fair(BLIND)
    fm, sm = fair(DEFAULT_PARAMS)
    print(f"\n  瞎起点           公平分 {f0:.4f} ± {s0:.4f}")
    print(f"  我量好填进去的   公平分 {fm:.4f} ± {sm:.4f}")

    best = dict(BLIND)
    bd = ev(best)
    rng = np.random.default_rng(7)
    for i in range(50):
        c = dict(best)
        k = list(BOUNDS)[rng.integers(0, len(BOUNDS))]
        lo, hi = BOUNDS[k]
        span = (hi - lo) * max(0.35 * (1 - i / 50), 0.03)
        c[k] = float(np.clip(c[k] + rng.normal(0, span), lo, hi))
        d = ev(c)
        if d < bd:
            best, bd = c, d

    f1, s1 = fair(best)
    print(f"  她学完           公平分 {f1:.4f} ± {s1:.4f}   （挑选分 {bd:.4f}）")
    print(f"\n  改善 {f0 - f1:+.4f}   2×标准误 {2 * max(s0, s1):.4f}   "
          f"{'✅ 真改善' if (f0 - f1) > 2 * max(s0, s1) else '❌ 在噪声里'}")
    print(f"  幅度 {(f0 - f1) / f0 * 100:.0f}%      比我的默认 {'好' if f1 < fm else '差'} "
          f"({f1:.4f} vs {fm:.4f})")

    print("\n  参数          瞎起点 → 学到      （我填的）")
    for k in BOUNDS:
        print(f"    {k:<14} {BLIND[k]:>7.3f} → {best[k]:>7.3f}     ({DEFAULT_PARAMS[k]:.3f})")

    # held-out：拿另一批真人当靶
    fh, _ = fair(best, T_test)
    fhb, _ = fair(BLIND, T_test)
    print(f"\n  held-out（{len(test)} 段没见过的真人当靶）："
          f"瞎起点 {fhb:.4f} → 她 {fh:.4f}   改善 {(fhb-fh)/fhb*100:.0f}%")

    json.dump({'blind': BLIND, 'learned': best, 'default': DEFAULT_PARAMS,
               'fair_blind': f0, 'fair_default': fm, 'fair_learned': f1,
               'se': [s0, sm, s1], 'heldout_blind': fhb, 'heldout_learned': fh,
               'real_targets_train': T_train, 'real_targets_test': T_test},
              open(os.path.join(os.path.dirname(__file__), '..', 'data',
                                'exp81b_speech_blind.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print("\n已写入 data/exp81b_speech_blind.json")


if __name__ == '__main__':
    main()
