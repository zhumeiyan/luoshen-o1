# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for c in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
          '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']:
    if os.path.exists(c):
        font_manager.fontManager.addfont(c)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=c).get_name()
        break
plt.rcParams['axes.unicode_minus'] = False

R = json.load(open(os.path.join(os.path.dirname(__file__), 'result105.json')))
fine = json.load(open(os.path.join(os.path.dirname(__file__), 'fine_scan.json')))
D = os.path.dirname(__file__)

fig, ax = plt.subplots(2, 2, figsize=(13, 9))

# (1) 剂量扫描 + 陡峭带
a = ax[0, 0]
ms = [float(k) for k in R['dose_scan'].keys()]
vs = [R['dose_scan'][k]['mean'] for k in R['dose_scan'].keys()]
al = [R['dose_scan'][k]['alive'] for k in R['dose_scan'].keys()]
a.semilogx(ms, vs, 'o-', color='#c0392b', lw=2, label='结构偏度')
a2 = a.twinx()
a2.semilogx(ms, al, 's--', color='#2980b9', lw=1.5, label='存活/16')
a2.set_ylim(0, 17); a2.set_ylabel('存活数', color='#2980b9')
fm = sorted([float(k) for k in fine.keys()])
fv = [fine[str(m)]['mean'] for m in fm]
a.semilogx(fm, fv, '^', color='#27ae60', ms=7, label='细扫描')
a.axvspan(2.0, 2.4, color='orange', alpha=0.20)
a.set_xlabel('收入倍数（×维持成本）'); a.set_ylabel('结构偏度')
a.set_title('① 收入剂量：结构在 2.0–2.4 相变归零')
a.grid(alpha=0.3); a.legend(loc='upper right', fontsize=8)

# (2) 主结果对比
a = ax[0, 1]
names = ['基线\n(稀缺)', '收入\n×2.0', '收入\n×2.2', '收入\n≥2.4']
vv = [R['baseline']['mean'], fine['2.0']['mean'], fine['2.2']['mean'], fine['2.4']['mean']]
aa = [R['baseline']['alive'], fine['2.0']['alive'], fine['2.2']['alive'], fine['2.4']['alive']]
bars = a.bar(names, vv, color=['#2c3e50', '#e67e22', '#f39c12', '#c0392b'])
for b, v, s in zip(bars, vv, aa):
    a.text(b.get_x() + b.get_width()/2, b.get_height() + 0.008,
           '%.4f\n存活%d' % (v, s), ha='center', fontsize=8)
a.set_ylabel('结构偏度'); a.set_ylim(0, 0.36)
a.set_title('② 钱买来存活，抹平结构')

# (3) 断供 / 随机
a = ax[1, 0]
labs = ['稳定充裕', '随机收入', '中段断供', '基线稀缺']
vals = [R['income_stable']['mean'], R['income_jitter']['mean'],
        R['income_cut']['mean'], R['baseline']['mean']]
cols = ['#c0392b', '#e67e22', '#f39c12', '#2c3e50']
b = a.barh(labs, vals, color=cols)
for i, v in enumerate(vals):
    a.text(v + 0.006, i, '%.4f' % v, va='center', fontsize=9)
a.set_xlabel('结构偏度'); a.set_xlim(0, 0.34)
a.set_title('③ 断供反而让结构回来')

# (4) 静默失效诊断
a = ax[1, 1]
dg = R['diag_silent_failure']
for k, col in zip(['x1.0', 'x3.0', 'x10.0'], ['#2c3e50', '#c0392b', '#8e44ad']):
    a.plot(range(8), dg[k]['capv'], 'o-', color=col, label='收入 %s (std=%.6f)' % (k, dg[k]['std']))
a.set_xlabel('通道'); a.set_ylabel('capacity')
a.set_title('④ 静默失效排除：×3 时全部顶到 1.0')
a.legend(fontsize=8); a.grid(alpha=0.3)

plt.tight_layout()
p = os.path.join(os.path.dirname(__file__), '..', '..', 'fig', '105_income.png')
plt.savefig(p, dpi=130)
print('saved', p)
