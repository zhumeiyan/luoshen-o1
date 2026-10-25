# -*- coding: utf-8 -*-
"""手 vs 眼 对称性 2x2 —— v4
v3: 眼噪效应被死亡筛选污染(存活 .938->.062)；手噪为白噪声被积分平滑掉。
v4 修正：
  眼噪 = 瞬时读取误差 sigma_in（世界没变，我看错了）
  手噪 = 行动强度的【系统性偏差】b（每个体固定，每次都偏同一边）——
         真实的手不准是校准误差，不是随机抖动，不会被平均掉
  分析 = 共同存活子集（剔除死亡筛选）
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try: from core.life5 import Life5
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
    from life5 import Life5

STEPS, PERIOD = 600, 80.0

def run(seed, eye, hand, k_seek_arr=0.6, k_act=0.05, decay=0.05, arr_thr=0.50,
        trace=False):
    rng = np.random.default_rng(seed * 7919 + 13)
    life = Life5(seed=seed, sigma_in=eye, k_seek=0.0,
                 k_seek_arr=k_seek_arr, arr_thr=arr_thr)
    bias = hand * rng.normal() if hand > 0 else 0.0   # 系统性偏差，全体固定
    act = 0.0; tr = []
    for t in range(STEPS):
        world = 0.5 + 0.3 * np.sin(2 * np.pi * t / PERIOD)
        life.input_val = world + act
        r = life.step()
        if r is None: break
        ten = float(life.sp[0] - life.y[0])
        a = float(np.clip(k_act * ten, 0.0, 0.10))
        a_eff = a * (1.0 + bias)
        act = float(np.clip(act + a_eff - decay * act, -0.5, 0.5))
        if trace: tr.append(act)
    cap = life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                skew=float(np.std(cap) / max(np.mean(cap), 1e-12)),
                act_final=float(act), bias=float(bias),
                act_range=(float(min(tr)), float(max(tr))) if trace else None)

def cell(eye, hand, n=16):
    rs = [run(s, eye, hand) for s in range(n)]
    return dict(rs=rs,
                skew=float(np.mean([r['skew'] for r in rs])),
                alive=float(np.mean([r['alive'] for r in rs])),
                skews=[r['skew'] for r in rs],
                alivev=[r['alive'] for r in rs])

def paired(a, b, nb=4000):
    a = np.asarray(a); b = np.asarray(b)
    d = a - b; n = len(d)
    rng = np.random.default_rng(0)
    bs = np.array([np.mean(rng.choice(d, n, True)) for _ in range(nb)])
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(diff=float(d.mean()), ci=[lo, hi], sig=bool((lo > 0) == (hi > 0)), n=int(n))

if __name__ == '__main__':
    print('=== 诊断：手的累积量是否撞 clip（撞了则效应被削）===')
    for h in (0.0, 0.30, 0.60):
        r = run(3, 0.0, h, trace=True)
        lo, hi = r['act_range']
        print(f"  hand={h:<5} bias={r['bias']:+.4f} act_final={r['act_final']:+.4f} "
              f"范围=[{lo:+.4f},{hi:+.4f}] {'撞clip!' if (hi>=0.499 or lo<=-0.499) else ''}")

    print('\n=== 阳性对照 ===')
    base = cell(0.0, 0.0)
    c_eye = cell(0.30, 0.0); c_hand = cell(0.0, 0.30)
    for nm, c in (('眼噪', c_eye), ('手噪', c_hand)):
        r = paired(c['skews'], base['skews'])
        print(f"  {nm}: {r['diff']:+.6f} CI=[{r['ci'][0]:+.6f},{r['ci'][1]:+.6f}] 显著={r['sig']} 存活={c['alive']:.3f}")

    print('\n=== 四格（全体）===')
    cells = {'e0.0_h0.0': base, 'e0.3_h0.0': c_eye,
             'e0.0_h0.3': c_hand, 'e0.3_h0.3': cell(0.30, 0.30)}
    for k, c in cells.items():
        print(f"  {k:12s} skew={c['skew']:.6f} 存活={c['alive']:.3f}")

    # 共同存活子集：四个格子都活下来的 seed
    alive_all = [i for i in range(16)
                 if all(cells[k]['alivev'][i] for k in cells)]
    print(f"\n=== 共同存活子集 n={len(alive_all)} ===")
    out = {}
    if len(alive_all) >= 4:
        bsub = [base['skews'][i] for i in alive_all]
        for k in cells:
            c = cells[k]
            sub = [c['skews'][i] for i in alive_all]
            r = paired(sub, bsub) if k != 'e0.0_h0.0' else \
                dict(diff=0.0, ci=[0.0, 0.0], sig=False, n=len(sub))
            out[k] = dict(skew=float(np.mean(sub)), **r)
            if k != 'e0.0_h0.0':
                print(f"  {k:12s} skew={np.mean(sub):.6f} diff={r['diff']:+.6f} "
                      f"CI=[{r['ci'][0]:+.6f},{r['ci'][1]:+.6f}] {'显著' if r['sig'] else '跨0'}")
            else:
                print(f"  {k:12s} skew={np.mean(sub):.6f} (基线)")
    json.dump(dict(cells={k: dict(skew=c['skew'], alive=c['alive'],
                                  skews=c['skews']) for k, c in cells.items()},
                   common=out, n_common=len(alive_all)),
              open('handeye4.json', 'w'), ensure_ascii=False, indent=1)
