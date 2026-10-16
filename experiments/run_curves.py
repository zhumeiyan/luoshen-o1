# -*- coding: utf-8 -*-
"""导出真实运行曲线（供绘图与演示视频使用）。写入 data/curves.json。"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from life5 import Life5   # noqa

STEPS, WARM = 600, 300
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, '..', 'data', 'curves.json')


def make_starver(ch, warm):
    def alloc(want, B, s):
        o = np.argsort(-want); a = np.zeros(s.N); left = B
        for i in o:
            if s.t < warm and i == ch:
                continue
            tk = min(want[i], left); a[i] = tk; left -= tk
            if left <= 1e-12:
                break
        return a
    return alloc


def ser(lf, key):
    return [float(r[key]) for r in lf.log]


def ch_share(lf, ch):
    return [float(r['avec'][ch] / max(sum(r['avec']), 1e-12)) for r in lf.log]


def cap_skew_series(lf):
    """逐拍结构偏度（capacity 的 std/mean）。"""
    out = []
    for r in lf.log:
        c = np.asarray(r['capv'], float)
        out.append(float(c.std(ddof=1) / max(c.mean(), 1e-12)))
    return out


d = {}

# 1) 生死对照：seed 3 会死，seed 5 会活
for sd in (3, 5):
    lf = Life5(N=8, seed=sd); lf.run(STEPS)
    d[f'life_seed{sd}'] = dict(seed=sd, survived=bool(lf.alive),
                               death_t=(None if lf.death_t is None else int(lf.death_t)),
                               E=ser(lf, 'E'), cap=ser(lf, 'cap'),
                               sp=ser(lf, 'sp'), alive=ser(lf, 'alive'))

# 2) 取舍实验：两组跑 ch3 份额曲线
for starve in (3, 5):
    lf = Life5(N=8, seed=5, alloc_fn=make_starver(starve, WARM)); lf.run(STEPS)
    d[f'tradeoff_starve{starve}'] = dict(starve=starve, warm=WARM,
                                         share3=ch_share(lf, 3), cap=ser(lf, 'cap'))

# 3) 稀缺 × 不可逆 2x2：capacity 疤痕曲线
for sc in (1, 0):
    for ir in (1, 0):
        kw = dict(N=8, seed=5)
        if not sc: kw['ratio'] = 50.0
        if not ir: kw['cap_decay'] = 0.0
        lf = Life5(**kw); lf.run(STEPS)
        d[f'weld_s{sc}_i{ir}'] = dict(cap=ser(lf, 'cap'),
                                      skew=cap_skew_series(lf))

# 4) 关键期：四个窗口的结构偏度曲线
wins = {'early': (0, 150), 'mid': (150, 300), 'late': (300, 450),
        'full': (0, STEPS), 'none': None}
d['window'] = {}
for name, win in wins.items():
    def mk(win):
        def alloc(want, B, s):
            if win is not None and win[0] <= s.t < win[1]:
                want = want.copy(); want[0] += 0.30 * want.sum()
            o = np.argsort(-want); a = np.zeros(s.N); left = B
            for i in o:
                tk = min(want[i], left); a[i] = tk; left -= tk
                if left <= 1e-12:
                    break
            return a
        return alloc
    lf = Life5(N=8, seed=5, alloc_fn=mk(win)); lf.run(STEPS)
    d['window'][name] = dict(skew=cap_skew_series(lf), win=win)

with open(OUT, 'w') as f:
    json.dump(d, f, ensure_ascii=False)
print('written ->', os.path.abspath(OUT))
print('seed3 death_t =', d['life_seed3']['death_t'], '| seed5 survived =', d['life_seed5']['survived'])
