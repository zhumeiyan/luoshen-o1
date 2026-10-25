# -*- coding: utf-8 -*-
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

d = json.load(open(os.path.join(OUT, 'result197.json')))
b = json.load(open(os.path.join(OUT, 'result197b.json')))
orc = d['oracle']

fig, ax = plt.subplots(2, 2, figsize=(13, 9))
COL = {'rest': '#4C72B0', 'replay': '#DD8452', 'dream': '#55A868', 'noise': '#C44E52'}

# ---- A: 四模式 ----
a0 = ax[0, 0]
modes = ['rest', 'replay', 'dream', 'noise']
vals = [d['A'][m]['steady'] for m in modes]
errs = [d['A'][m]['std'] for m in modes]
a0.bar([m for m in modes], vals, yerr=errs, color=[COL[m] for m in modes],
       capsize=4, alpha=.85)
a0.axhline(orc, ls='--', c='k', lw=1.2)
a0.text(3.4, orc + .012, f'oracle {orc}', ha='right', fontsize=9)
a0.set_ylabel('稳态预测误差 MAE（越低越好）')
a0.set_title('A  离线期四种过法\n做梦 ≠ 更好', fontsize=11)
for i, v in enumerate(vals):
    a0.text(i, v + .012, f'{v:.4f}', ha='center', fontsize=9)

# ---- Q1: 剂量反应 ----
a1 = ax[0, 1]
q1 = [r for r in b['Q1'] if isinstance(r['p_bad'], float)]
q1.sort(key=lambda r: r['p_bad'])
xs = [r['p_bad'] for r in q1]
ys = [r['mae'] for r in q1]
ss = [r.get('std', 0) for r in q1]
a1.errorbar(xs, ys, yerr=ss, fmt='o-', c='#55A868', capsize=3, ms=6)
a1.set_xscale('symlog', linthresh=0.02)
a1.set_xlabel('重放样本中"动力学错误"的比例 p')
a1.set_ylabel('MAE')
a1.set_title('Q1  荒诞的代价：错误越多越笨\n（端点 0→0.920, 1→1.012）', fontsize=11)
a1.grid(alpha=.3)

# ---- Q2: 在线稀缺度 ----
a2 = ax[1, 0]
q2 = b['Q2']
xs = [r['N_on'] for r in q2]
for m in ['rest', 'replay', 'dream']:
    a2.plot(xs, [r[m] for r in q2], 'o-', c=COL[m], label=m, ms=5)
a2.axhline(orc, ls='--', c='k', lw=1)
a2.set_xlabel('每天在线步数 N_on')
a2.set_ylabel('MAE')
a2.set_title('Q2  在线越久越瞎（感知疲劳复现 195）\n且 rest 几乎总是最优', fontsize=11)
a2.legend(fontsize=9)
a2.grid(alpha=.3)

# ---- Q3: 离线预算 ----
a3 = ax[1, 1]
q3 = b['Q3']
xs = [r['B_off'] for r in q3]
a3.plot(xs, [r['replay'] for r in q3], 'o-', c=COL['replay'], label='replay 保真重放', ms=5)
a3.plot(xs, [r['dream'] for r in q3], 's-', c=COL['dream'], label='dream 重组重放', ms=5)
a3.axhline(orc, ls='--', c='k', lw=1)
a3.set_xlabel('离线重放预算 B_off（步）')
a3.set_ylabel('MAE')
a3.set_title('Q3  重放越多越差\n离线预算 0 时反而是最优', fontsize=11)
a3.legend(fontsize=9)
a3.grid(alpha=.3)

plt.suptitle('197  动态捕捉 + 记忆 + 决策 + 梦境（MAE 越低越好）',
             fontsize=13, y=0.985)
plt.tight_layout(rect=[0, 0, 1, 0.965])
p = os.path.join(OUT, 'render197.png')
plt.savefig(p, dpi=130)
print('saved', p, os.path.getsize(p), 'bytes')
