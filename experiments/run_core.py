# -*- coding: utf-8 -*-
"""
洛神 O1 · 核心结论复现脚本（四项）

用法：
    python3 experiments/run_core.py            # 全跑，写 data/core_results.json
    python3 experiments/run_core.py --quick    # 只跑 A（死亡扫描）

原则：所有数字由本脚本当场跑出，不读存档、不写死常量。
"""
import sys, os, json, argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
try:
    from core.life5 import Life5   # 装包运行（pip install .）
except ImportError:               # 源码运行（core/ 直接在 sys.path）
    from life5 import Life5   # noqa

STEPS = 600
WARM = 300          # 取舍实验的"饿"窗口


def make_starver(ch, warm):
    """前 warm 拍强制不给通道 ch 分配（真实硬取舍），之后完全放开。"""
    def alloc(want, B, s):
        o = np.argsort(-want)
        a = np.zeros(s.N)
        left = B
        for i in o:
            if s.t < warm and i == ch:
                continue
            tk = min(want[i], left)
            a[i] = tk
            left -= tk
            if left <= 1e-12:
                break
        return a
    return alloc


def run(lf, steps=STEPS):
    lf.run(steps)
    return lf


def tail_share(lf, ch, warm=WARM):
    """后段（warm 之后）该通道的平均份额。"""
    recs = [r for r in lf.log if r['t'] > warm]
    if not recs:
        return float('nan')
    return float(np.mean([r['avec'][ch] / max(sum(r['avec']), 1e-12) for r in recs]))


def struct_skew(lf):
    """终态结构偏度：capacity 相对均匀的差异（std/mean）。"""
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


# ---------- A. 死亡扫描：它会死 ----------
def exp_A(seeds=range(16)):
    out = []
    for sd in seeds:
        lf = Life5(N=8, seed=sd)
        run(lf, STEPS)
        out.append(dict(seed=int(sd), survived=bool(lf.alive),
                        death_t=(None if lf.death_t is None else int(lf.death_t)),
                        final_E=float(lf.E), final_cap=float(np.mean(lf.capacity))))
    return out


# ---------- B. 撤掉全部决策模块，取舍依然出现 ----------
def exp_B(seeds=range(8), probe=3):
    """决策模块 = 寻找(k_seek)、显著性(k_sal)、arrival预测(k_seek_arr)、KPI(kpi_push)，
    全部保持引擎默认 0 —— 即"没有决策模块"。
    前 300 拍分别饿通道 3 / 通道 5，之后两组的条件完全相同；
    两组都测【同一个探针通道 probe=3】的后段份额。"""
    rows = []
    for sd in seeds:
        sh = {}
        for starve in (3, 5):
            lf = Life5(N=8, seed=sd, alloc_fn=make_starver(starve, WARM))
            run(lf, STEPS)
            sh[starve] = tail_share(lf, probe)
        r = dict(seed=int(sd), share_s3=sh[3], share_s5=sh[5],
                 delta=sh[3] - sh[5])
        rows.append(r)
    d = np.array([r['delta'] for r in rows])
    neg = int(np.sum(d < 0))
    return dict(rows=rows, probe=probe,
                mean_s3=float(np.mean([r['share_s3'] for r in rows])),
                mean_s5=float(np.mean([r['share_s5'] for r in rows])),
                mean_delta=float(d.mean()), se=float(d.std(ddof=1)/np.sqrt(len(d))),
                sign_consistent=neg, n=len(rows))


# ---------- C. 稀缺 × 不可逆 是焊死的 ----------
def exp_C(seeds=range(8)):
    """2x2：稀缺开/关 × 不可逆开/关。
    稀缺关 = ratio 极大（要多少给多少）；不可逆关 = cap_decay=0。
    看：终态 capacity 是否形成疤痕 / 是否塌回均匀。"""
    res = {}
    for sc in (True, False):
        for ir in (True, False):
            key = f"scarcity_{int(sc)}_irrev_{int(ir)}"
            vals = []
            for sd in seeds:
                kw = dict(N=8, seed=sd)
                if not sc:
                    kw['ratio'] = 50.0       # 预算极大 → 不再取舍
                if not ir:
                    kw['cap_decay'] = 0.0    # 不留疤
                lf = Life5(**kw)
                run(lf, STEPS)
                vals.append(struct_skew(lf))
            v = np.array(vals)
            res[key] = dict(mean_skew=float(v.mean()), se=float(v.std(ddof=1)/np.sqrt(len(v))))
    return res


# ---------- D. 关键期：早期引导撤除后保留多少 ----------
def exp_D(seeds=range(8), kpi=0.30):
    """外部引导（kpi_push）在不同窗口施加，看终态结构偏度的保留率。
    窗口：早期 0-150 / 中期 150-300 / 晚期 300-450 / 全程 / 无。"""
    wins = {'early': (0, 150), 'mid': (150, 300), 'late': (300, 450),
            'full': (0, STEPS), 'none': None}

    def run_window(win, sd):
        lf = Life5(N=8, seed=sd)

        def alloc(want, B, s):
            if win is not None and win[0] <= s.t < win[1]:
                want = want.copy()
                want[0] += kpi * want.sum()
            o = np.argsort(-want)
            a = np.zeros(s.N)
            left = B
            for i in o:
                tk = min(want[i], left)
                a[i] = tk
                left -= tk
                if left <= 1e-12:
                    break
            return a
        lf.alloc_fn = alloc
        run(lf, STEPS)
        return struct_skew(lf)

    res = {}
    for name, win in wins.items():
        v = np.array([run_window(win, sd) for sd in seeds])
        res[name] = dict(mean=float(v.mean()), se=float(v.std(ddof=1)/np.sqrt(len(v))))
    base = res['none']['mean']
    full = res['full']['mean']
    res['_retention'] = float((res['early']['mean'] - base) / (full - base)) if abs(full - base) > 1e-9 else None
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--steps', type=int, default=STEPS)
    a = ap.parse_args()
    STEPS = a.steps
    out = {}
    print('[A] 死亡扫描 ...', flush=True)
    out['A_death'] = exp_A()
    if not a.quick:
        print('[B] 无决策模块的取舍 ...', flush=True)
        out['B_tradeoff'] = exp_B()
        print('[C] 稀缺×不可逆 ...', flush=True)
        out['C_weld'] = exp_C()
        print('[D] 关键期 ...', flush=True)
        out['D_window'] = exp_D()
    p = os.path.join(os.path.dirname(__file__), '..', 'data', 'core_results.json')
    with open(p, 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
    print('written ->', p)
