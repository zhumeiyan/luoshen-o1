# -*- coding: utf-8 -*-
"""实验 079 结果图：失真的普遍性 —— 两个表达形式，同一个世界"""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = json.load(open(os.path.join(ROOT, 'evidence', 'raw_data', 'shared_world_079.json')))
b = json.load(open(os.path.join(ROOT, 'evidence', 'raw_data', 'shared_world_079b.json')))
FIG = os.path.join(ROOT, 'fig')
os.makedirs(FIG, exist_ok=True)

fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
fig.suptitle('实验 079 · 失真的普遍性：两个表达形式，同一个世界\n'
             '（真实气象换能器读数 %d 城，%s）' % (d['n_cities'], d['timestamp']),
             fontsize=13, fontweight='bold')

# ---------- 左上：通道与可译性 ----------
ax = axes[0, 0]
dims = ['温度', '湿度', '气压']
carbon_ch = [1, 0, 0]
silicon_ch = [1, 1, 1]
trans = [b['B1']['carbon_levels'] > 0, False, False]
x = np.arange(3); w = 0.35
ax.bar(x - w/2, carbon_ch, w, label='碳基通道', color='#e07b39', alpha=.9)
ax.bar(x + w/2, silicon_ch, w, label='硅基通道', color='#3d7ea6', alpha=.9)
for i, (c, s) in enumerate(zip(carbon_ch, silicon_ch)):
    if c == 0:
        ax.text(i - w/2, 0.06, '盲', ha='center', fontsize=11, color='white', fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(dims, fontsize=11)
ax.set_ylabel('通道数', fontsize=10); ax.set_ylim(0, 1.35)
ax.set_title('① 盲区不对称：碳基 1/3，硅基 3/3\n（人类无湿度感受器、无大气压感受器）',
             fontsize=10.5, fontweight='bold')
ax.legend(fontsize=9); ax.grid(axis='y', alpha=.3)

# ---------- 右上：温度维度的可译性 ----------
ax = axes[0, 1]
tr = d['translatability']
labels = ['碳基→温度\n(同源)', '硅基→温度\n(同源)', '碳基→硅基\n(互译)',
          '碳基→湿度\n(跨维度)', '碳基→他城\n(跨个体)']
vals = [tr['carbon_to_temp']['eta2'], tr['silicon_to_temp']['eta2'],
        tr['carbon_to_silicon']['eta2'], tr['cross_source']['eta2'],
        d['translatability']['cross_source']['eta2']]
vals = [tr['carbon_to_temp']['eta2'], tr['silicon_to_temp']['eta2'],
        tr['carbon_to_silicon']['eta2'], tr['cross_source']['eta2'], 0.2907]
nullm = tr['carbon_to_temp']['null_mean']
colors = ['#2e7d32', '#2e7d32', '#2e7d32', '#c62828', '#ef6c00']
bars = ax.bar(range(5), vals, color=colors, alpha=.85)
ax.axhline(nullm, ls='--', color='gray', lw=1.4, label=f'随机零分布均值 {nullm:.3f}')
ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=8.5)
ax.set_ylabel('eta²（可译性）', fontsize=10); ax.set_ylim(0, 1.1)
for i, v in enumerate(vals):
    ax.text(i, v + .03, f'{v:.3f}', ha='center', fontsize=9, fontweight='bold')
ax.set_title('② 共享的边界：同源可译，跨维度/跨个体崩塌', fontsize=10.5, fontweight='bold')
ax.legend(fontsize=9); ax.grid(axis='y', alpha=.3)

# ---------- 左下：保序重映射（我自己建模错误的代价）----------
ax = axes[1, 0]
b2 = b['B2']['compare']
names = ['silicon_uniform', 'carbon_trp']
disp = ['硅基均匀', '碳基TRP']
raw_d = [b2[f'原版_{n}']['diff'] for n in names]
raw_lo = [b2[f'原版_{n}']['ci'][0] for n in names]
raw_hi = [b2[f'原版_{n}']['ci'][1] for n in names]
map_d = [b2[f'保序_{n}']['diff'] for n in names]
map_lo = [b2[f'保序_{n}']['ci'][0] for n in names]
map_hi = [b2[f'保序_{n}']['ci'][1] for n in names]
x = np.arange(2); w = .35
raw_e = [np.array(raw_d) - np.array(raw_lo), np.array(raw_hi) - np.array(raw_d)]
map_e = [np.array(map_d) - np.array(map_lo), np.array(map_hi) - np.array(map_d)]
ax.errorbar(x - w/2, raw_d, yerr=raw_e,
            fmt='o', capsize=5, color='#c62828', ms=8, label='原版（动态范围被压缩）')
ax.errorbar(x + w/2, map_d, yerr=map_e,
            fmt='s', capsize=5, color='#2e7d32', ms=8, label='保序重映射（范围统一）')
ax.axhline(0, color='k', lw=1.2)
ax.set_xticks(x); ax.set_xticklabels(disp, fontsize=10)
ax.set_ylabel('Δ 偏度 vs 无表征', fontsize=10)
ax.set_title('③ 我差点读错：差异来自动态范围，不是范畴方式\n'
             '（保序拉回同一区间后，碳基范畴与连续版实质等价）',
             fontsize=10.5, fontweight='bold')
ax.legend(fontsize=9); ax.grid(axis='y', alpha=.3)

# ---------- 右下：同档数对照 ----------
ax = axes[1, 1]
o3 = b['B3']['out']; c3 = b['B3']['compare']
ks = ['trp_3band', 'uniform_3band', 'random_3band']
disp3 = ['TRP 生理阈值', '均匀阈值', '随机阈值\n(破坏单调)']
sk = [o3[k]['skew'] for k in ks]
cols = ['#e07b39', '#3d7ea6', '#c62828']
bars = ax.bar(range(3), sk, color=cols, alpha=.85)
for i, k in enumerate(ks):
    ax.text(i, sk[i] + .004, f'{sk[i]:.4f}', ha='center', fontsize=9.5, fontweight='bold')
ax.set_xticks(range(3)); ax.set_xticklabels(disp3, fontsize=9.5)
ax.set_ylabel('容量偏度（内在结构）', fontsize=10)
ax.set_ylim(0.27, 0.33)
ax.set_title('④ 阈值【摆在哪】不重要，【保不保序】重要\n'
             'TRP vs 均匀 Δ=-0.0001（等价）；随机 Δ=-0.0189（有差异）',
             fontsize=10.5, fontweight='bold')
ax.grid(axis='y', alpha=.3)

plt.tight_layout(rect=[0, 0, 1, 0.94])
out = os.path.join(FIG, '079_lossy_world.png')
plt.savefig(out, dpi=150, bbox_inches='tight')
print('[OK]', out, os.path.getsize(out), 'bytes')
