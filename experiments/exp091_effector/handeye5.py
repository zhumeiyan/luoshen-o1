# -*- coding: utf-8 -*-
"""决定性对照：区分"是手/眼之别"还是"可预测/不可预测之别"。
条件：
  base   无误差
  eye    sigma_in=0.30            世界没变，我看错了（每拍随机）
  h_bias 手·系统性偏差 0.30        我每次都偏同一边（可预测，持久）
  h_rand 手·每拍随机 0.30          我每拍抖，直接改变世界（不可预测）
关键：eye 与 h_rand 在 sense 处数学上同构（都是给 sense 加每拍独立噪声）。
若两者效应相同 => 系统【内省无法区分"看错"和"做错"】，区别只在本体论。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try: from core.life5 import Life5
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
    from life5 import Life5
STEPS, PERIOD, KSA = 600, 80.0, 0.1

def run(seed, mode, mag=0.30, k_act=0.05, decay=0.05, arr_thr=0.50):
    rng = np.random.default_rng(seed * 7919 + 13)
    eye = mag if mode == 'eye' else 0.0
    life = Life5(seed=seed, sigma_in=eye, k_seek=0.0, k_seek_arr=KSA, arr_thr=arr_thr)
    bias = mag * rng.normal() if mode == 'h_bias' else 0.0
    act = 0.0; flip = 0; prev = None
    for t in range(STEPS):
        world = 0.5 + 0.3 * np.sin(2 * np.pi * t / PERIOD)
        act_term = act
        if mode == 'h_rand':
            act_term = act + mag * rng.normal()
        life.input_val = world + act_term
        r = life.step()
        if r is None: break
        if prev is not None and r['arrival'] != prev: flip += 1
        prev = r['arrival']
        ten = float(life.sp[0] - life.y[0])
        a = float(np.clip(k_act * ten, 0.0, 0.10))
        act = float(np.clip(act + a * (1.0 + bias) - decay * act, -0.5, 0.5))
    cap = life.capacity
    return dict(seed=int(seed), alive=bool(life.alive), flip=flip,
                skew=float(np.std(cap) / max(np.mean(cap), 1e-12)))

def cell(mode, n=16):
    rs = [run(s, mode) for s in range(n)]
    return dict(mode=mode, skew=float(np.mean([r['skew'] for r in rs])),
                alive=float(np.mean([r['alive'] for r in rs])),
                flip=float(np.mean([r['flip'] for r in rs])),
                skews=[r['skew'] for r in rs], alivev=[r['alive'] for r in rs])

def paired(a, b, nb=4000):
    d = np.asarray(a) - np.asarray(b); n = len(d)
    rng = np.random.default_rng(0)
    bs = np.array([np.mean(rng.choice(d, n, True)) for _ in range(nb)])
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(diff=float(d.mean()), ci=[lo, hi], sig=bool((lo > 0) == (hi > 0)))

if __name__ == '__main__':
    modes = ['base', 'eye', 'h_bias', 'h_rand']
    C = {m: cell(m) for m in modes}
    print(f"{'条件':<8}{'skew':<12}{'存活':<8}{'arrival翻转':<12}{'diff':<12}{'CI'}")
    for m in modes:
        c = C[m]
        r = paired(c['skews'], C['base']['skews']) if m != 'base' else dict(diff=0., ci=[0, 0], sig=False)
        print(f"{m:<8}{c['skew']:<12.6f}{c['alive']:<8.3f}{c['flip']:<12.1f}"
              f"{r['diff']:<+12.6f}[{r['ci'][0]:+.5f},{r['ci'][1]:+.5f}]{'*' if r['sig'] else ''}")
    # 共同存活子集
    idx = [i for i in range(16) if all(C[m]['alivev'][i] for m in modes)]
    print(f"\n=== 共同存活子集 n={len(idx)} ===")
    if len(idx) >= 4:
        bs = [C['base']['skews'][i] for i in idx]
        for m in modes:
            sub = [C[m]['skews'][i] for i in idx]
            if m == 'base':
                print(f"  base    skew={np.mean(sub):.6f} (基线)")
            else:
                r = paired(sub, bs)
                print(f"  {m:<8}skew={np.mean(sub):.6f} diff={r['diff']:+.6f} "
                      f"CI=[{r['ci'][0]:+.5f},{r['ci'][1]:+.5f}] {'显著' if r['sig'] else '跨0'}")
    # 眼 vs 手随机：是否可区分
    r_eh = paired(C['eye']['skews'], C['h_rand']['skews'])
    print(f"\n=== 眼噪 vs 手·随机（同构？）===")
    print(f"  eye - h_rand = {r_eh['diff']:+.6f} CI=[{r_eh['ci'][0]:+.5f},{r_eh['ci'][1]:+.5f}] "
          f"{'可区分' if r_eh['sig'] else '不可区分（内省无法分辨看错/做错）'}")
    json.dump(dict(cells={m: dict(skew=C[m]['skew'], alive=C[m]['alive'],
                                  flip=C[m]['flip'], skews=C[m]['skews'],
                                  alivev=C[m]['alivev']) for m in modes},
                   eye_vs_hrand=r_eh, n_common=len(idx)),
              open('handeye5.json', 'w'), ensure_ascii=False, indent=1)
