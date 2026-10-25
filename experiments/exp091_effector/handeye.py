# -*- coding: utf-8 -*-
"""手（效应器）vs 眼（感受器）对称性 2x2。
眼噪 sigma_in、手噪 eff_sigma 分别取 0 / 0.30，闭环：
  眼看到 env -> 内部张力 -> 伸手去够(行动) -> 实际生效量受手噪扰动 -> 改变 env
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from core.life5 import Life5
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
    from life5 import Life5

STEPS = 600

def run(seed, eye_noise, hand_noise, k_act=0.05, gain=1.0, decay=0.02):
    rng = np.random.default_rng(seed * 7919 + 13)
    life = Life5(seed=seed, sigma_in=eye_noise)
    env = 0.5
    for t in range(STEPS):
        life.input_val = env
        life.step()
        if not life.alive:
            break
        # 内部张力驱动"伸手去够"
        tension = float(life.sp[0] - life.y[0])
        a = float(np.clip(k_act * tension, 0.0, 0.10))
        a_eff = a * (1.0 + hand_noise * rng.normal()) if hand_noise > 0 else a
        env = env + gain * a_eff - decay
        env = float(np.clip(env, -1.0, 1.0))
    cap = life.capacity
    skew = float(np.std(cap) / max(np.mean(cap), 1e-12))
    return dict(seed=int(seed), alive=bool(life.alive),
                death_t=life.death_t, skew=skew,
                env_final=float(env))

def cell(eye, hand, n=16):
    rs = [run(s, eye, hand) for s in range(n)]
    sk = np.array([r['skew'] for r in rs])
    al = np.array([r['alive'] for r in rs], dtype=float)
    return dict(eye=eye, hand=hand, n=n,
                skew=float(sk.mean()), skew_sd=float(sk.std()),
                alive_rate=float(al.mean()),
                skews=[float(x) for x in sk])

def paired_diff(a, b):
    """a - b 配对差 + bootstrap 95%CI"""
    x = np.array(a); y = np.array(b)
    n = len(x); d = x - y
    rng = np.random.default_rng(0)
    bs = np.array([np.mean(rng.choice(d, n, replace=True)) for _ in range(2000)])
    return dict(diff=float(d.mean()),
                ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])

if __name__ == '__main__':
    cells = {}
    for eye in (0.0, 0.30):
        for hand in (0.0, 0.30):
            c = cell(eye, hand)
            cells[f'e{eye}_h{hand}'] = c
            print(f"eye={eye:<5} hand={hand:<5} skew={c['skew']:.6f} "
                  f"(sd {c['skew_sd']:.4f}) 存活={c['alive_rate']:.3f}")

    base = cells['e0.0_h0.0']['skews']
    print('\n=== 配对差 vs 基线(眼0/手0)，bootstrap 95%CI ===')
    out = {}
    for k, c in cells.items():
        if k == 'e0.0_h0.0': continue
        r = paired_diff(c['skews'], base)
        out[k] = r
        print(f"  {k:12s} diff={r['diff']:+.6f} CI=[{r['ci'][0]:+.6f},{r['ci'][1]:+.6f}] "
              f"{'显著' if (r['ci'][0]>0)==(r['ci'][1]>0) else '跨0不显著'}")

    # 主效应：只动眼 vs 只动手
    eye_only = paired_diff(cells['e0.3_h0.0']['skews'], base)
    hand_only = paired_diff(cells['e0.0_h0.3']['skews'], base)
    both = paired_diff(cells['e0.3_h0.3']['skews'], base)
    print('\n=== 主效应 ===')
    print(f"  只劣化眼: {eye_only['diff']:+.6f} CI={eye_only['ci']}")
    print(f"  只劣化手: {hand_only['diff']:+.6f} CI={hand_only['ci']}")
    print(f"  两者都劣: {both['diff']:+.6f} CI={both['ci']}")
    json.dump(dict(cells=cells, diffs=out,
                   main=dict(eye=eye_only, hand=hand_only, both=both)),
              open('handeye.json', 'w'), ensure_ascii=False, indent=1)
