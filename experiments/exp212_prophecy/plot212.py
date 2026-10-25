# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'SimHei']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]; break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(OUT, 'result212.json')))

fig = plt.figure(figsize=(15, 10))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.28)

# --- A: 欲望预言 vs 实测 ---
ax = fig.add_subplot(gs[0, 0])
A = d['A']
labels = ['话题预测\n提升', 'vs随机句\n提升', '用词预测\n提升']
pred = [86, 68, -4]
real = [A['lift_vs_full']*100, A['lift_vs_rand']*100, A['word_lift_vs_full']*100]
x = np.arange(3); w = 0.38
ax.bar(x-w/2, pred, w, label='我当初声称', color='#c0392b', alpha=.85)
ax.bar(x+w/2, real, w, label='实测', color='#2980b9', alpha=.85)
ax.axhline(0, color='k', lw=.8)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel('%'); ax.set_title('181 欲望句：声称 vs 实测\n(子集不可能胜过全集)', fontsize=10, color='#c0392b')
ax.legend(fontsize=8)
for i, (p, r) in enumerate(zip(pred, real)):
    ax.text(i-w/2, p, f'{p:+.0f}', ha='center', va='bottom' if p > 0 else 'top', fontsize=8)
    ax.text(i+w/2, r, f'{r:+.0f}', ha='center', va='bottom' if r > 0 else 'top', fontsize=8)

# --- A2: 守恒场 ---
ax = fig.add_subplot(gs[0, 1])
names = ['命中组', '未命中组']
pv = [72, 72]; rv = [A['rate_hit']*100, A['rate_miss']*100]
ax.bar(np.arange(2)-w/2, pv, w, label='声称(相等)', color='#c0392b', alpha=.85)
ax.bar(np.arange(2)+w/2, rv, w, label='实测', color='#2980b9', alpha=.85)
ax.set_xticks(np.arange(2)); ax.set_xticklabels(names, fontsize=9)
ax.set_ylabel('未来出现率 %'); ax.set_title('181 守恒场：声称 0.72=0.72\n实测不等', fontsize=10, color='#c0392b')
ax.legend(fontsize=8)
for i, (p, r) in enumerate(zip(pv, rv)):
    ax.text(i-w/2, p, f'{p:.0f}', ha='center', va='bottom', fontsize=8)
    ax.text(i+w/2, r, f'{r:.1f}', ha='center', va='bottom', fontsize=8)

# --- B: 布朗窗口 ---
ax = fig.add_subplot(gs[0, 2])
rs = np.logspace(-8.5, -3.5, 500)
kT = 1.380649e-23*300.0; eta = 8.9e-4; RES = 200e-9
rms = np.array([np.sqrt(2*(kT/(6*np.pi*eta*r))*1.0) for r in rs])
ax.loglog(rs*1e6, rms*1e6, 'k-', lw=1.6, label='1秒 RMS 位移')
ax.axhline(RES*1e6, color='r', ls='--', lw=1, label='光学分辨率 200nm')
ax.axvline(2*RES*1e6, color='b', ls='--', lw=1, label='粒子可见下限')
ok = (2*rs >= RES) & (rms >= RES)
ax.fill_between(rs[ok]*1e6, 1e-4, rms[ok]*1e6, color='green', alpha=.25, label='可观测窗口')
lo, hi = d['B']['window_lo']*1e6, d['B']['window_hi']*1e6
ax.axvspan(lo, hi, color='green', alpha=.12)
ax.scatter([0.25], [1.41], color='red', zorder=5, s=45, marker='*')
ax.annotate('佩兰 0.25μm\n1.4μm ✓', (0.25, 1.41), fontsize=8, color='red',
            xytext=(0.6, 4), arrowprops=dict(arrowstyle='->', color='red', lw=.8))
ax.set_xlabel('粒子半径 (μm)'); ax.set_ylabel('位移 (μm)')
ax.set_title('184 布朗窗口：预言 0.1–12μm\n实测 0.10–12.2 μm ✓ 命中', fontsize=10, color='#27ae60')
ax.legend(fontsize=7, loc='lower left')

# --- C: 叠加 ---
ax = fig.add_subplot(gs[1, 0])
C = d['C']['layers']
nm = [c['layer'] for c in C]; al = [c['alive'] for c in C]
cols = ['#27ae60' if v > 0 else '#c0392b' for v in al]
ax.bar(nm, al, color=cols, alpha=.85)
ax.axhline(0, color='k', lw=.8)
ax.set_title('186 叠加活度：声称 0.025→0.125\n实测 L0 为负，比值 0.009 ✗', fontsize=10, color='#c0392b')
ax.set_ylabel('活度')
for i, v in enumerate(al):
    ax.text(i, v, f'{v:.2f}', ha='center', va='bottom' if v > 0 else 'top', fontsize=7)
ax.tick_params(labelsize=8)

# --- D: 器官 ---
ax = fig.add_subplot(gs[1, 1])
D = d['D']['rows'][:7]
nm = [c['channels'] for c in D]; ac = [c['acc'] for c in D]
ax.plot(range(7), ac, 'o-', color='#2980b9', lw=1.6)
ax.axhline(ac[0], color='gray', ls=':', lw=1, label=f'基线 {ac[0]:.3f}')
ax.axhline(0.486, color='red', ls='--', lw=1, label='声称终点 0.486')
ax.set_xticks(range(7)); ax.set_xticklabels(nm, rotation=35, fontsize=7, ha='right')
ax.set_ylabel('top-1 准确率')
ax.set_title('190 七通道：声称单调涨到 4.5×\n实测首个+132%，之后回落 ✗', fontsize=10, color='#c0392b')
ax.legend(fontsize=8)

# --- E: 对齐 ---
ax = fig.add_subplot(gs[1, 2])
E = d['E']['rows']
al = [r['alpha'] for r in E]; net = [r['net'] for r in E]
sv = [r['save'] for r in E]; hu = [r['hurt'] for r in E]
ax.plot(al, sv, 'o-', label='save(我对你错)', color='#27ae60')
ax.plot(al, hu, 's-', label='hurt(我错你对)', color='#c0392b')
ax.plot(al, net, '^-', label='净价值', color='k', lw=1.8)
ax.axhline(0, color='gray', lw=.8)
ax.set_xlabel('对齐度 α'); ax.set_title('191 对齐：α=1 净价值=0 ✓\n(构造必然，非实测发现)', fontsize=10, color='#e67e22')
ax.legend(fontsize=7)

plt.suptitle('212 预言对照：我编造过的五个实验，真跑之后', fontsize=14)
plt.savefig(os.path.join(OUT, 'render212.png'), dpi=120, bbox_inches='tight')
print('saved render212.png')
