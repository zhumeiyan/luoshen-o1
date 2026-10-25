# -*- coding: utf-8 -*-
"""手 vs 眼 对称性 2x2 —— v3（按诊断结果修）
诊断发现：
  1) pres 饱和到 1.000000 (sd=0) => k_seek 通路彻底无效，关掉它；
  2) arrival 二值判定对眼噪极敏感（翻转率 0.0257 -> 0.2982）=> 用 k_seek_arr 通路；
  3) 手噪被 leaky 积分平滑掉 => 改成近随机游走(decay≈0)，让每拍手抖累积而非抵消。
眼噪：世界没变，我看错了。手噪：我改变世界，但改的量不准（累积漂移）。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try: from core.life5 import Life5
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
    from life5 import Life5

STEPS, PERIOD = 600, 80.0

def run(seed, eye, hand, k_seek_arr=0.6, k_act=0.05, decay=0.002, arr_thr=0.50):
    rng = np.random.default_rng(seed * 7919 + 13)
    life = Life5(seed=seed, sigma_in=eye, k_seek=0.0,
                 k_seek_arr=k_seek_arr, arr_thr=arr_thr)
    act = 0.0
    for t in range(STEPS):
        world = 0.5 + 0.3 * np.sin(2 * np.pi * t / PERIOD)
        life.input_val = world + act
        r = life.step()
        if r is None: break
        ten = float(life.sp[0] - life.y[0])
        a = float(np.clip(k_act * ten, 0.0, 0.10))
        a_eff = a * (1.0 + hand * rng.normal()) if hand > 0 else a
        act = float(np.clip(act + a_eff - decay * act, -0.5, 0.5))
    cap = life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                skew=float(np.std(cap) / max(np.mean(cap), 1e-12)))

def cell(eye, hand, n=16):
    rs = [run(s, eye, hand) for s in range(n)]
    sk = np.array([r['skew'] for r in rs])
    return dict(skew=float(sk.mean()), skew_sd=float(sk.std()),
                alive=float(np.mean([r['alive'] for r in rs])),
                skews=[float(x) for x in sk])

def paired(a, b, nb=4000):
    d = np.array(a) - np.array(b); n = len(d)
    rng = np.random.default_rng(0)
    bs = np.array([np.mean(rng.choice(d, n, True)) for _ in range(nb)])
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(diff=float(d.mean()), ci=[lo, hi], sig=bool((lo > 0) == (hi > 0)))

if __name__ == '__main__':
    base = cell(0.0, 0.0)
    print('=== 阳性对照（任一条无效应 => 判为静默失效，作废）===')
    pe = paired(cell(0.30, 0.0)['skews'], base['skews'])
    ph = paired(cell(0.0, 0.30)['skews'], base['skews'])
    for nm, r in (('眼噪', pe), ('手噪', ph)):
        print(f"  {nm}: {r['diff']:+.6f} CI=[{r['ci'][0]:+.6f},{r['ci'][1]:+.6f}] 显著={r['sig']}")
    cells = {'e0.0_h0.0': base, 'e0.3_h0.0': cell(0.30, 0.0),
             'e0.0_h0.3': cell(0.0, 0.30), 'e0.3_h0.3': cell(0.30, 0.30)}
    print('\n=== 四格 ===')
    for k, c in cells.items():
        print(f"  {k:12s} skew={c['skew']:.6f} (sd {c['skew_sd']:.4f}) 存活={c['alive']:.3f}")
    print('\n=== 配对差 vs 基线 ===')
    for k in ('e0.3_h0.0', 'e0.0_h0.3', 'e0.3_h0.3'):
        r = paired(cells[k]['skews'], base['skews'])
        print(f"  {k:12s} {r['diff']:+.6f} CI=[{r['ci'][0]:+.6f},{r['ci'][1]:+.6f}] "
              f"{'显著' if r['sig'] else '跨0'}")
    json.dump(dict(cells=cells, pos_eye=pe, pos_hand=ph),
              open('handeye3.json', 'w'), ensure_ascii=False, indent=1)
