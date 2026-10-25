# -*- coding: utf-8 -*-
"""把 data/ 里的真实运行结果画成图。所有像素来自当场跑出的数据。"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, '..')
FIG = os.path.join(ROOT, 'fig')
os.makedirs(FIG, exist_ok=True)

# ---------- 中文字体 ----------
CAND = ['/usr/share/fonts/truetype/alibaba-puhuiti/AlibabaPuHuiTi-2-75-SemiBold.ttf',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']
FONT = None
for p in CAND:
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
        FONT = font_manager.FontProperties(fname=p)
        break
if FONT is not None:
    plt.rcParams['font.family'] = FONT.get_name()
plt.rcParams['axes.unicode_minus'] = False

BG = '#0d1117'
FG = '#e6edf3'
ACC = '#58a6ff'
RED = '#f85149'
GRN = '#3fb950'
YEL = '#d29922'
PUR = '#bc8cff'

cur = json.load(open(os.path.join(ROOT, 'data', 'curves.json')))
res = json.load(open(os.path.join(ROOT, 'data', 'core_results.json')))


def style(ax, title, xlab, ylab):
    ax.set_facecolor(BG)
    ax.set_title(title, color=FG, fontsize=17, pad=14, fontweight='bold')
    ax.set_xlabel(xlab, color='#8b949e', fontsize=12)
    ax.set_ylabel(ylab, color='#8b949e', fontsize=12)
    ax.tick_params(colors='#8b949e', labelsize=10.5)
    for s in ax.spines.values():
        s.set_color('#30363d')
    ax.grid(True, color='#21262d', lw=0.8, alpha=0.9)


def save(fig, name):
    fig.patch.set_facecolor(BG)
    fig.tight_layout()
    p = os.path.join(FIG, name)
    fig.savefig(p, dpi=150, facecolor=BG)
    plt.close(fig)
    print('  ->', name)


# ---------- 图1：它会死 ----------
d3, d5 = cur['life_seed3'], cur['life_seed5']
fig, ax = plt.subplots(figsize=(11, 5.6))
t3 = np.arange(len(d3['E']))
t5 = np.arange(len(d5['E']))
ax.plot(t5, d5['E'], color=GRN, lw=2.2, label=f"seed 5 · 存活 (E_final={d5['E'][-1]:.3f})")
ax.plot(t3, d3['E'], color=RED, lw=2.2, label=f"seed 3 · 死亡于第 {d3['death_t']} 拍")
ax.axhline(0.0, color='#484f58', ls='--', lw=1.2)
if d3['death_t'] is not None:
    ax.axvline(d3['death_t'], color=RED, ls=':', lw=1.6, alpha=0.8)
    ax.annotate('E=0 且持续超过耐心阈值\n→ 运行终止，不回滚',
                xy=(d3['death_t'], 0.02), xytext=(d3['death_t'] - 250, 0.30),
                color=RED, fontsize=12, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=RED, lw=1.5))
style(ax, '死亡是真实结局，不是异常分支', '拍 (step)', '能量 E')
ax.legend(facecolor=BG, edgecolor='#30363d', labelcolor=FG, fontsize=12, loc='upper right')
ax.set_ylim(-0.05, 1.08)
save(fig, 'fig1_death.png')

# ---------- 图2：无决策模块的取舍 ----------
s3 = cur['tradeoff_starve3']
s5 = cur['tradeoff_starve5']
fig, ax = plt.subplots(figsize=(11, 5.6))
x = np.arange(len(s3['share3']))
ax.plot(x, s3['share3'], color=RED, lw=2.4, label='前 300 拍饿通道 3 → 后段通道 3 份额')
ax.plot(x, s5['share3'], color=ACC, lw=2.4, label='前 300 拍饿通道 5 → 后段通道 3 份额')
ax.axvspan(0, 300, color='#6e7681', alpha=0.16)
ax.text(150, max(max(s3['share3']), max(s5['share3'])) * 0.88, '饥饿窗口',
        ha='center', color='#8b949e', fontsize=12)
ax.axvline(300, color=YEL, ls='--', lw=1.4)
ax.text(310, max(max(s3['share3']), max(s5['share3'])) * 0.88,
        '此后两组条件完全相同', color=YEL, fontsize=12)
b = res['B_tradeoff']
ax.text(0.985, 0.06, f"Δ = {b['mean_delta']:+.3f} ± {b['se']:.3f} (SE, n=8)\n"
                     f"符号一致 {b['sign_consistent']}/{b['n']} seeds\n"
                     f"决策模块全部关闭",
        transform=ax.transAxes, ha='right', va='bottom', color=FG, fontsize=12.5,
        bbox=dict(fc='#161b22', ec='#30363d', pad=8))
style(ax, '关掉全部决策模块，取舍依然出现', '拍 (step)', '通道 3 的资源份额')
ax.legend(facecolor=BG, edgecolor='#30363d', labelcolor=FG, fontsize=12, loc='upper left')
save(fig, 'fig2_tradeoff.png')

# ---------- 图3：稀缺 × 不可逆焊死 ----------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4))
lab = {(1, 1): '稀缺 在 不可逆 在', (1, 0): '稀缺 在 不可逆 撤',
       (0, 1): '稀缺 撤 不可逆 在', (0, 0): '稀缺 撤 不可逆 撤'}
col = {(1, 1): GRN, (1, 0): RED, (0, 1): RED, (0, 0): '#6e7681'}
for (sc, ir), c in col.items():
    k = f'weld_s{sc}_i{ir}'
    ax1.plot(cur[k]['cap'], color=c, lw=2.3, label=lab[(sc, ir)])
style(ax1, '结构疤痕：只有两条同时成立才出现', '拍 (step)', '平均容量 capacity（只减不增）')
ax1.legend(facecolor=BG, edgecolor='#30363d', labelcolor=FG, fontsize=11, loc='lower left')

c = res['C_weld']
keys = ['scarcity_1_irrev_1', 'scarcity_1_irrev_0', 'scarcity_0_irrev_1', 'scarcity_0_irrev_0']
names = ['两条\n都在', '撤掉\n不可逆', '撤掉\n稀缺', '两条\n都撤']
vals = [c[k]['mean_skew'] for k in keys]
errs = [c[k]['se'] for k in keys]
bars = ax2.bar(names, vals, yerr=errs, capsize=6,
               color=[GRN, RED, RED, '#6e7681'], edgecolor='#30363d')
ax2.bar_label(bars, fmt='%.3f', color=FG, fontsize=12, padding=4)
style(ax2, '终态结构偏度（n=8）', '', 'std/mean of capacity')
ax2.set_ylim(0, max(vals) * 1.35)
save(fig, 'fig3_weld.png')

# ---------- 图4：关键期 ----------
fig, ax = plt.subplots(figsize=(11, 5.6))
for name, col_, lb in [('early', GRN, '早期 0–150 施加后撤除'),
                       ('mid', YEL, '中期 150–300'),
                       ('late', RED, '晚期 300–450'),
                       ('full', PUR, '全程施加'),
                       ('none', '#6e7681', '全程无引导')]:
    ax.plot(cur['window'][name]['skew'], color=col_, lw=2.3, label=lb)
w = res['D_window']
ax.text(0.985, 0.045,
        f"早期 {w['early']['mean']:.3f} ± {w['early']['se']:.3f}\n"
        f"中期 {w['mid']['mean']:.3f} ± {w['mid']['se']:.3f}\n"
        f"晚期 {w['late']['mean']:.3f} ± {w['late']['se']:.3f}\n"
        f"全程 {w['full']['mean']:.3f} ± {w['full']['se']:.3f}\n"
        f"无引导 {w['none']['mean']:.3f} ± {w['none']['se']:.3f}",
        transform=ax.transAxes, ha='right', va='bottom', color=FG, fontsize=12,
        bbox=dict(fc='#161b22', ec='#30363d', pad=8))
style(ax, '结构有关键期：早期给过，撤掉之后还在', '拍 (step)', '结构偏度 std/mean of capacity')
ax.legend(facecolor=BG, edgecolor='#30363d', labelcolor=FG, fontsize=11.5, loc='upper left')
save(fig, 'fig4_window.png')

# ---------- 图5：死亡扫描 ----------
A = res['A_death']
fig, ax = plt.subplots(figsize=(11, 4.6))
seeds = [r['seed'] for r in A]
surv = [r['survived'] for r in A]
cols = [GRN if s else RED for s in surv]
ax.bar(seeds, [1]*len(seeds), color=cols, edgecolor='#30363d')
for r, s in zip(A, seeds):
    ax.text(s, 1.06, '活' if r['survived'] else f"死\n{r['death_t']}",
            ha='center', color=(GRN if r['survived'] else RED), fontsize=11, fontweight='bold')
ax.set_yticks([])
style(ax, f'16 个种子真实跑一遍：{sum(surv)} 活 / {len(surv)-sum(surv)} 死', 'seed', '')
ax.set_xlim(-0.7, len(seeds) - 0.3)
ax.set_ylim(0, 1.35)
save(fig, 'fig5_deathscan.png')
print('ALL DONE')
