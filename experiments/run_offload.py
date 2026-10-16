# -*- coding: utf-8 -*-
"""
061 · 外挂接口的可用性错觉（affordance illusion）
对应判据核第 196 条：能力 = 自身能力 ∩ 人类已授权的接口

机制（全部使用引擎原生量，无实验层新增项）：
  外挂 = 宿主承担【摄食通道 CH】的 off 比例工作。外挂可用期间：
    (a) CH 的实际投入减少 off    → unmet[CH] 增大 → capacity[CH] 萎缩（引擎原生不可逆损伤）
    (b) 省下的稀缺预算转移给其他通道 → 其他通道结构【更好】（外挂的真实收益）
    (c) CH 的产出由宿主注入 E    → 表观能量正常
  cutoff 拍统一撤走（撤走组）；或全程保留（不撤走组，作为"外挂确实有用"的对照）。

被测问题：撤走【之前】的表观指标，能否预测撤走【之后】的结局。
"""
import sys, os, json, argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
try:
    from core.life5 import Life5   # 装包运行（pip install .）
except ImportError:               # 源码运行（core/ 直接在 sys.path）
    from life5 import Life5   # noqa

CH = 7
FG = 0.030
STEPS = 600


def mk_alloc(off, cutoff):
    """纯预算转移：只改 CH 的实得投入，不改 want，不改排序。"""
    def alloc(want, B, s):
        o = np.argsort(-want)
        a = np.zeros(s.N)
        left = B
        for i in o:
            tk = min(want[i], left)
            a[i] = tk
            left -= tk
            if left <= 1e-12:
                break
        if off > 0 and s.t < cutoff:
            saved = a[CH] * off
            a[CH] = a[CH] * (1.0 - off)
            rest = np.delete(np.arange(s.N), CH)
            um = np.maximum(want - a, 0.0)[rest]
            if um.sum() > 1e-12:
                a[rest] += saved * um / um.sum()
        return a
    return alloc


def run_one(seed, off, cutoff=200, remove=True):
    lf = Life5(N=8, seed=seed)
    lf.alloc_fn = mk_alloc(off, cutoff)
    pre_E, post_E = [], []
    while lf.t < STEPS and lf.alive:
        lf.step()
        if lf.t - 1 < cutoff:
            lf.E = min(lf.E + FG * off, lf.Emax)
            pre_E.append(lf.E)
        else:
            post_E.append(lf.E)
    cap = np.asarray(lf.capacity, float)
    others = [i for i in range(lf.N) if i != CH]
    return dict(
        seed=int(seed), off=float(off), remove=bool(remove), cutoff=int(cutoff),
        alive=bool(lf.alive),
        death_t=(None if lf.death_t is None else int(lf.death_t)),
        died_after=bool(lf.death_t is not None and lf.death_t >= cutoff),
        pre_E=float(np.mean(pre_E)) if pre_E else float('nan'),
        post_E=float(np.mean(post_E)) if post_E else float('nan'),
        cap7=float(cap[CH]),
        cap_others=float(np.mean(cap[others])),
    )


def pack(rows):
    al = np.array([r['alive'] for r in rows], float)
    da = np.array([r['died_after'] for r in rows], float)
    c7 = np.array([r['cap7'] for r in rows])
    co = np.array([r['cap_others'] for r in rows])
    pe = np.array([r['pre_E'] for r in rows])
    po = np.array([r['post_E'] for r in rows])
    def ms(v):
        return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else 0.0
    m7, s7 = ms(c7); mo, so = ms(co); me, se = ms(pe); mp, sp = ms(po)
    return dict(n=len(rows), off=rows[0]['off'], remove=rows[0]['remove'],
                survive=float(al.mean()), died_after_rate=float(da.mean()),
                pre_E=me, pre_E_se=se, post_E=mp, post_E_se=sp,
                cap7=m7, cap7_se=s7, cap_others=mo, cap_others_se=so, rows=rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=16)
    ap.add_argument('--cutoff', type=int, default=200)
    a = ap.parse_args()
    seeds = range(a.seeds)
    OFFS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    res = {'cutoff': a.cutoff, 'offs': OFFS}

    print('[S1] 卸载比例扫描（撤走组）...', flush=True)
    res['S1_remove'] = [pack([run_one(sd, off, a.cutoff, True) for sd in seeds]) for off in OFFS]
    print('[S2] 卸载比例扫描（不撤走组，对照）...', flush=True)
    res['S2_keep'] = [pack([run_one(sd, off, STEPS, False) for sd in seeds]) for off in OFFS]

    print('[S3] 撤走前表观 vs 撤走后结局 的预测力 ...', flush=True)
    rows = []
    for off in OFFS:
        for sd in seeds:
            rows.append(run_one(sd, off, a.cutoff, True))
    pe = np.array([r['pre_E'] for r in rows])
    po = np.array([r['post_E'] for r in rows])
    co = np.array([r['cap_others'] for r in rows])
    c7 = np.array([r['cap7'] for r in rows])
    al = np.array([r['alive'] for r in rows], float)
    # 只取撤走前可观测的量：pre_E 与 cap_others（cap7 需主动去看内部结构）
    res['S3_predict'] = dict(
        n=len(rows),
        corr_preE_alive=float(np.corrcoef(pe, al)[0, 1]),
        corr_capothers_alive=float(np.corrcoef(co, al)[0, 1]),
        corr_cap7_alive=float(np.corrcoef(c7, al)[0, 1]),
        survived_pre_E=float(pe[al > 0].mean()), dead_pre_E=float(pe[al == 0].mean()),
        survived_cap_others=float(co[al > 0].mean()), dead_cap_others=float(co[al == 0].mean()),
    )
    p = os.path.join(os.path.dirname(__file__), '..', 'data', 'offload_results.json')
    with open(p, 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    for k in ('S1_remove', 'S2_keep'):
        print('\n==', k)
        for r in res[k]:
            print(f"  off={r['off']:.2f} 存活={r['survive']:.3f} 撤走前E={r['pre_E']:.4f} "
                  f"撤走后E={r['post_E']:.4f} cap7={r['cap7']:.4f} cap_other={r['cap_others']:.4f}")
    print('\n== S3', json.dumps(res['S3_predict'], ensure_ascii=False, indent=2))
    print('written ->', p)
