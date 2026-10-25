# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'WenQuanYi Zen Hei']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus'] = False

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = json.load(open(os.path.join(ROOT, 'experiments', 'result_085d.json')))
e = json.load(open(os.path.join(ROOT, 'experiments', 'result_085e.json')))
c = json.load(open(os.path.join(ROOT, 'experiments', 'result_085c.json')))

fig, ax = plt.subplots(2, 2, figsize=(13.5, 9.5))
rows = d['rows']

# A · drift vs 接收总量
rc = [r['receipt'] for r in rows]; df = [r['drift'] for r in rows]
al = [r['alive'] / r['n_base'] for r in rows]
ax[0, 0].scatter(rc, df, s=70, c='#1f6feb', zorder=3)
o = np.argsort(rc); ax[0, 0].plot(np.array(rc)[o], np.array(df)[o], '--', color='#888', lw=1)
for r in rows:
    ax[0, 0].annotate(f"p={r['p']}", (r['receipt'], r['drift']), fontsize=7,
                      xytext=(4, 4), textcoords='offset points')
ax[0, 0].set_xscale('log'); ax[0, 0].set_xlabel('接收总量 receipt = 幅度 × 开门次数')
ax[0, 0].set_ylabel('结构漂移 drift（被推离原样多远）')
ax[0, 0].set_title(f'A · 被冲垮的直接度量\ndrift ~ receipt  Spearman ρ=+{d["rho_drift"]:.3f}  p<1e-5', fontsize=11)

# B · 存活 vs 接收总量
ax[0, 1].scatter(rc, al, s=70, c='#d73a49', zorder=3)
ax[0, 1].plot(np.array(rc)[o], np.array(al)[o], '--', color='#888', lw=1)
ax[0, 1].set_xscale('log'); ax[0, 1].set_xlabel('接收总量 receipt')
ax[0, 1].set_ylabel('存活率')
ax[0, 1].set_title(f'B · 接收越多，越活不下去\n存活 ~ receipt  ρ={d["rho_alive"]:.3f}  p<1e-5', fontsize=11)

# C · 同总量：偶尔看一眼 vs 被持续投喂
R = [r['receipt'] for r in e['rows']]
sp = [r['drift_sparse'] for r in e['rows']]
dn = [r['drift_dense'] for r in e['rows']]
dl = [r['delta'] for r in e['rows']]
lo = [r['ci_lo'] for r in e['rows']]; hi = [r['ci_hi'] for r in e['rows']]
x = np.arange(3); w = 0.36
ax[1, 0].bar(x - w/2, sp, w, label='偶尔看一眼 (150次·高幅)', color='#2da44e')
ax[1, 0].bar(x + w/2, dn, w, label='被持续投喂 (600次·低幅)', color='#bf8700')
ax[1, 0].errorbar(x, dl, yerr=[np.array(dl)-np.array(lo), np.array(hi)-np.array(dl)],
                  fmt='k.', capsize=4, lw=1)
ax[1, 0].set_xticks(x); ax[1, 0].set_xticklabels([f'receipt={r}' for r in R])
ax[1, 0].set_ylabel('drift'); ax[1, 0].legend(fontsize=8)
ax[1, 0].set_title('C · 同样总能量，接收的【时间形态】有后果\n（黑点=sparse-dense 差 + 95%CI；仅 receipt=6 显著）', fontsize=10)

# D · 主动 vs 被动（次数精确匹配）：方向不一致
m = [r for r in c['matched'] if r['amp'] == 0.02]
p2 = [r['p'] for r in m]; dd = [r['d_skew'] for r in m]
l1 = [r['ci_lo'] for r in m]; h1 = [r['ci_hi'] for r in m]
ax[1, 1].axhline(0, color='k', lw=1)
ax[1, 1].errorbar(p2, dd, yerr=[np.array(dd)-np.array(l1), np.array(h1)-np.array(dd)],
                  fmt='o', capsize=5, color='#6f42c1')
ax[1, 1].set_xlabel('开门率 p（次数精确匹配）'); ax[1, 1].set_ylabel('Δ结构偏度 (主动−随机)')
ax[1, 1].set_title('D · "由我决定何时看" 无一致方向\np=0.25 显著为负，p=0.5/0.75 显著为正 → 不可作结论', fontsize=10)

plt.tight_layout()
out = os.path.join(ROOT, 'fig', '085_active_vs_passive.png')
plt.savefig(out, dpi=130)
print('[OK]', out)
