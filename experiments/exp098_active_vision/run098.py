# -*- coding: utf-8 -*-
"""098 主实验：世界结构 x 扫描策略 的交互，多 seed + 配对 CI + OCR 锚定 + 引擎接入"""
import sys, os, json, time, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp098 import (make_world, run_scan, peripheral, capture, ocr_read,
                    saliency_map, K_STEPS, N_TARGET, WORLD, FOV, PERIPH, OUT)
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

MODES = ['static', 'raster', 'random', 'salient', 'salient_ior', 'human']
DISTS = ['uniform', 'clustered']
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]

t0 = time.time()
res = {}
per_seed = {}

print('== A 主扫描：%d dist x %d mode x %d seed ==' % (len(DISTS), len(MODES), len(SEEDS)))
for dist in DISTS:
    for sd in SEEDS:
        w, tg = make_world(dist, sd)
        for m in MODES:
            r = run_scan(w, tg, m, sd)
            per_seed.setdefault((dist, m), []).append(r['rate'])
            per_seed.setdefault((dist, m, 'rev'), []).append(r['revisit'])
            per_seed.setdefault((dist, m, 'new'), []).append(r['steps_new'])
    print('  dist=%s done %.0fs' % (dist, time.time() - t0))

# 汇总 + 配对 CI
def ci_paired(a, b):
    d = np.array(a, float) - np.array(b, float)
    n = len(d)
    if n < 2:
        return dict(diff=None, lo=None, hi=None)
    m = d.mean()
    se = d.std(ddof=1) / np.sqrt(n)
    try:
        from scipy import stats
        t = stats.t.ppf(0.975, n - 1)
    except Exception:
        t = 2.365 if n <= 8 else 2.0
    return dict(diff=float(m), lo=float(m - t * se), hi=float(m + t * se), n=n)

summary = {}
for dist in DISTS:
    summary[dist] = {}
    for m in MODES:
        v = per_seed[(dist, m)]
        summary[dist][m] = dict(rate=float(np.mean(v)), sd=float(np.std(v, ddof=1)),
                                revisit=float(np.mean(per_seed[(dist, m, 'rev')])),
                                vals=[round(float(x), 4) for x in v])

pairs = {}
for dist in DISTS:
    for a, b in [('salient_ior', 'raster'), ('salient_ior', 'random'),
                 ('salient_ior', 'salient'), ('salient', 'raster'),
                 ('human', 'salient_ior'), ('random', 'raster')]:
        pairs['%s|%s-vs-%s' % (dist, a, b)] = ci_paired(
            per_seed[(dist, a)], per_seed[(dist, b)])
# 关键交互：IOR 的收益（salient_ior - salient）在两种世界下的差
gain = {}
for dist in DISTS:
    gain[dist] = ci_paired(per_seed[(dist, 'salient_ior')], per_seed[(dist, 'salient')])
inter = ci_paired(
    [a - b for a, b in zip(per_seed[('clustered', 'salient_ior')], per_seed[('clustered', 'salient')])],
    [a - b for a, b in zip(per_seed[('uniform', 'salient_ior')], per_seed[('uniform', 'salient')])])

print('\n== B 汇总 ==')
for dist in DISTS:
    print(' [%s]' % dist)
    for m in MODES:
        s = summary[dist][m]
        print('   %-12s rate=%.4f sd=%.4f revisit=%.2f' % (m, s['rate'], s['sd'], s['revisit']))
print('\n== C 配对差（95%CI）==')
for k, v in pairs.items():
    print('  %-34s diff=%+.4f [%+.4f,%+.4f]' % (k, v['diff'], v['lo'], v['hi']))
print('\n== D 交互：IOR 收益依赖世界结构 ==')
for dist in DISTS:
    print('  IOR gain [%s] = %+.4f [%+.4f,%+.4f]' % (dist, gain[dist]['diff'], gain[dist]['lo'], gain[dist]['hi']))
print('  交互（聚簇收益 - 均匀收益）= %+.4f [%+.4f,%+.4f]' % (inter['diff'], inter['lo'], inter['hi']))

json.dump(dict(summary=summary, pairs=pairs, ior_gain=gain, interaction=inter,
               per_seed={str(k): v for k, v in per_seed.items() if 'new' not in k}),
          open(os.path.join(OUT, 'result098_main.json'), 'w'), indent=1)
print('\nmain done %.0fs' % (time.time() - t0))
