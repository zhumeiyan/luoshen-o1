#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'SimHei']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]
        break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False

B = '/data/workspace/luoshen-o1/experiments/exp178_search'
c = json.load(open(B + '/result178c.json', encoding='utf-8'))
d = json.load(open(B + '/result178d.json', encoding='utf-8'))


def m(xs):
    return sum(xs) / len(xs)


fig, ax = plt.subplots(1, 3, figsize=(16.5, 4.8))

# 左: 迷茫程度 vs 外部相对优势
bands = range(10)
surp = [m([r['bands'][b]['mean_surp'] for r in c]) for b in bands]
adv = [m([r['bands'][b]['adv_ext_over_int'] for r in c]) for b in bands]
hh = [m([r['bands'][b]['mean_H'] for r in c]) for b in bands]
ax[0].plot(bands, adv, 'o-', color='#c0392b', lw=2, label='外部-内部 (bits)')
ax[0].set_xlabel('按迷茫程度(H)分档  0=最有把握 → 9=最迷茫')
ax[0].set_ylabel('外部相对内部 (bits)', color='#c0392b')
ax[0].axhline(0, color='gray', ls=':', lw=1)
ax[0].set_title('我越迷茫, 外部相对越不差\n(但全程为负: 外部永远不能替代我)', fontsize=11)
a2 = ax[0].twinx()
a2.plot(bands, surp, 's--', color='#2c3e50', lw=1.5, label='我的惊讶')
a2.set_ylabel('我的惊讶 (bits)', color='#2c3e50')
ax[0].grid(alpha=.3)

# 中: 该信外部多少
lams = ['0.05', '0.10', '0.20', '0.30', '0.50', '0.70', '1.00']
xs = [float(x) for x in lams]
for Xf, col in [('X0.10', '#7f8c8d'), ('X0.20', '#2980b9'),
                ('X0.30', '#c0392b'), ('X0.50', '#27ae60')]:
    ys = [m([r['lam_sweep'][Xf][l] for r in c]) for l in lams]
    ax[1].plot(xs, ys, 'o-', color=col, lw=2, label='搜' + Xf[1:] + '的位置')
ax[1].axhline(0, color='k', lw=.8)
ax[1].set_xscale('log')
ax[1].set_xticks(xs)
ax[1].set_xticklabels(lams)
ax[1].set_xlabel('信任外部的程度 λ')
ax[1].set_ylabel('bits/字符 变化 (负=改善)')
ax[1].set_title('最优 λ≈0.2~0.3, 全信外部(λ=1)是灾难', fontsize=11)
ax[1].legend(fontsize=8)
ax[1].grid(alpha=.3)

# 右: 收益来自信息还是平滑
names = ['real', 'shuffled', 'self']
labels = ['真外部', '打乱的外部\n(只剩字符频率)', '自己当外部\n(对照)']
keys = [('by_adv', '按优势选', '#c0392b'), ('by_H', '按迷茫感选', '#2980b9'),
        ('rand', '随机', '#7f8c8d'), ('all', '全盘', '#27ae60')]
import numpy as np
w = 0.2
for j, (k, lab, col) in enumerate(keys):
    vals = [m([r[k] for r in d[n]]) for n in names]
    ax[2].bar(np.arange(3) + j * w - 0.3, vals, w, label=lab, color=col)
ax[2].set_xticks(np.arange(3))
ax[2].set_xticklabels(labels, fontsize=9)
ax[2].axhline(0, color='k', lw=.8)
ax[2].set_ylabel('bits/字符 变化')
ax[2].set_title('收益分解: 真信息只占 35%\n(-0.878 vs 打乱 -0.568)', fontsize=11)
ax[2].legend(fontsize=8)
ax[2].grid(alpha=.3, axis='y')

plt.tight_layout()
plt.savefig(B + '/render178.png', dpi=110)
print('saved', B + '/render178.png')
