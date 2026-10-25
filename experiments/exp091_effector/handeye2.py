# -*- coding: utf-8 -*-
"""手 vs 眼 对称性 2x2  —— v2：修好通路 + 阳性对照。
v1 失败原因：sense 只经 k_sal/k_seek/k_seek_arr 影响 want，三者默认 0
            => 噪声根本没进系统（判据核第 23 条，本项目第 12 次）。
修法：k_seek=0.6 打开"感知->缺失感->want[0]"通路；世界自带节律保证 sense 有变化。
眼噪 sigma_in：世界没变，我看错了。
手噪 eff_sigma：我改变世界，但改的量不准。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from core.life5 import Life5
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
    from life5 import Life5

STEPS, PERIOD = 600, 80.0

def run(seed, eye_noise, hand_noise, k_seek=0.6, k_act=0.05, gain=1.0, decay=0.05):
    rng = np.random.default_rng(seed * 7919 + 13)
    life = Life5(seed=seed, sigma_in=eye_noise, k_seek=k_seek)
    act_cum = 0.0
    for t in range(STEPS):
        world = 0.5 + 0.3 * np.sin(2 * np.pi * t / PERIOD)   # 世界自主节律
        life.input_val = world + act_cum                      # 手改变了世界
        life.step()
        if not life.alive:
            break
        tension = float(life.sp[0] - life.y[0])
        a = float(np.clip(k_act * tension, 0.0, 0.10))
        a_eff = a * (1.0 + hand_noise * rng.normal()) if hand_noise > 0 else a
        act_cum = act_cum + gain * a_eff - decay * act_cum
        act_cum = float(np.clip(act_cum, -0.5, 0.5))
    cap = life.capacity
    return dict(seed=int(seed), alive=bool(life.alive), death_t=life.death_t,
                skew=float(np.std(cap) / max(np.mean(cap), 1e-12)),
                act_final=float(act_cum))

def cell(eye, hand, n=16):
    rs = [run(s, eye, hand) for s in range(n)]
    sk = np.array([r['skew'] for r in rs])
    return dict(eye=eye, hand=hand, n=n, skew=float(sk.mean()),
                skew_sd=float(sk.std()),
                alive_rate=float(np.mean([r['alive'] for r in rs])),
                skews=[float(x) for x in sk])

def paired(a, b, nb=4000):
    d = np.array(a) - np.array(b); n = len(d)
    rng = np.random.default_rng(0)
    bs = np.array([np.mean(rng.choice(d, n, True)) for _ in range(nb)])
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(diff=float(d.mean()), ci=[lo, hi], sig=bool((lo > 0) == (hi > 0)))

if __name__ == '__main__':
    print('=== 阳性对照：通路是否真的接通（任一条无效应即作废）===')
    pos_eye = paired(cell(0.30, 0.0)['skews'], cell(0.0, 0.0)['skews'])
    pos_hand = paired(cell(0.0, 0.30)['skews'], cell(0.0, 0.0)['skews'])
    print(f"  眼噪单独: {pos_eye['diff']:+.6f} CI={[round(x,5) for x in pos_eye['ci']]} 显著={pos_eye['sig']}")
    print(f"  手噪单独: {pos_hand['diff']:+.6f} CI={[round(x,5) for x in pos_hand['ci']]} 显著={pos_hand['sig']}")
    if not (pos_eye['sig'] or pos_hand['sig']):
        print('  !! 两条通路都未接通，实验作废'); sys.exit(1)

    cells = {}
    for eye in (0.0, 0.30):
        for hand in (0.0, 0.30):
            c = cell(eye, hand); cells[f'e{eye}_h{hand}'] = c
            print(f"  eye={eye:<5} hand={hand:<5} skew={c['skew']:.6f} "
                  f"(sd {c['skew_sd']:.4f}) 存活={c['alive_rate']:.3f}")
    base = cells['e0.0_h0.0']['skews']
    print('\n=== 配对差 vs 基线 ===')
    for k, c in cells.items():
        if k == 'e0.0_h0.0': continue
        r = paired(c['skews'], base)
        print(f"  {k:12s} {r['diff']:+.6f} CI=[{r['ci'][0]:+.6f},{r['ci'][1]:+.6f}] "
              f"{'显著' if r['sig'] else '跨0'}")
    json.dump(dict(cells=cells, pos_eye=pos_eye, pos_hand=pos_hand),
              open('handeye2.json', 'w'), ensure_ascii=False, indent=1)
