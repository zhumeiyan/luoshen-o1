#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""095 出图 + 显著性检验"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for fp in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
           '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc']:
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.dirname(os.path.abspath(__file__))
FIG = '/data/workspace/luoshen-o1/fig'
os.makedirs(FIG, exist_ok=True)
R = json.load(open(os.path.join(OUT, 'result095.json')))
Rc = json.load(open(os.path.join(OUT, 'result095c.json')))

# ---------- 统计 ----------
def fisher(a, b, c, d):
    """2x2 Fisher 精确检验（双侧），纯 python 实现"""
    from math import comb
    n = a + b + c + d
    r1, r2, c1 = a + b, c + d, a + c
    def p_tab(x):
        return comb(r1, x) * comb(r2, c1 - x) / comb(n, c1)
    p_obs = p_tab(a)
    tot = 0.0
    for x in range(max(0, c1 - r2), min(r1, c1) + 1):
        p = p_tab(x)
        if p <= p_obs + 1e-12:
            tot += p
    return tot

stat = {}

# C: closed(14/16) vs blind(0/16) ; closed vs open(0/16)
n = R['C_play']['closed']['n']
h_closed = int(round(R['C_play']['closed']['rate'] * n))
h_blind = int(round(R['C_play']['blind']['rate'] * n))
h_open = int(round(R['C_play']['open']['rate'] * n))
stat['closed_vs_blind'] = dict(a=h_closed, b=n - h_closed, c=h_blind, d=n - h_blind,
                               p=fisher(h_closed, n - h_closed, h_blind, n - h_blind))
stat['closed_vs_open'] = dict(a=h_closed, b=n - h_closed, c=h_open, d=n - h_open,
                              p=fisher(h_closed, n - h_closed, h_open, n - h_open))

# D: lag=1 时 naive vs 补偿
nD = R['D_lag']['1']['naive']['n']
hn = int(round(R['D_lag']['1']['naive']['rate'] * nD))
hp = int(round(R['D_lag']['1']['pred']['rate'] * nD))
stat['lag1_naive_vs_pred'] = dict(a=hn, b=nD - hn, c=hp, d=nD - hp,
                                  p=fisher(hn, nD - hn, hp, nD - hp))
# D: 补偿在 lag=0 vs lag=8（补偿窗口的极限）
h0 = int(round(R['D_lag']['0']['pred']['rate'] * nD))
h8 = int(round(R['D_lag']['8']['pred']['rate'] * nD))
stat['pred_lag0_vs_lag8'] = dict(a=h0, b=nD - h0, c=h8, d=nD - h8,
                                 p=fisher(h0, nD - h0, h8, nD - h8))

# E: 25列 vs 6列（阈值）
nE = R['E_res']['25']['n']
h25 = int(round(R['E_res']['25']['rate'] * nE))
h6 = int(round(R['E_res']['6']['rate'] * nE))
stat['res25_vs_res6'] = dict(a=h25, b=nE - h25, c=h6, d=nE - h6,
                             p=fisher(h25, nE - h25, h6, nE - h6))

# G: 峰值（T=6000 时 256 vs 8）
nG = Rc['6000.0']['256']['n']
h256 = int(round(Rc['6000.0']['256']['rate'] * nG))
h8c = int(round(Rc['6000.0']['8']['rate'] * nG))
stat['peak256_vs_8'] = dict(a=h256, b=nG - h256, c=h8c, d=nG - h8c,
                            p=fisher(h256, nG - h256, h8c, nG - h8c))

print('=== 显著性检验（Fisher 双侧）===')
for k, v in stat.items():
    print(f'  {k:22s} {v["a"]}/{v["a"]+v["b"]} vs {v["c"]}/{v["c"]+v["d"]}   p={v["p"]:.4g}')
json.dump(stat, open(os.path.join(OUT, 'stat095.json'), 'w'), ensure_ascii=False, indent=1)

# ---------- 图 ----------
fig, ax = plt.subplots(2, 2, figsize=(14, 10))

# (a) 玩法
axa = ax[0, 0]
modes = ['oracle', 'closed', 'blind', 'open']
lbl = ['oracle\n(知道真值)', 'closed\n只看画面', 'blind\n不看', 'open\n无反馈']
vals = [R['C_play'][m]['rate'] for m in modes]
cols = ['#cccccc', '#2a7fbf', '#c0504d', '#c0504d']
b = axa.bar(lbl, vals, color=cols)
for r, v in zip(b, vals):
    axa.text(r.get_x() + r.get_width() / 2, v + 0.03, f'{v:.3f}', ha='center', fontsize=11)
axa.set_ylim(0, 1.18)
axa.set_ylabel('命中率')
axa.set_title('(a) 松手判据只来自画面后：不看 = 必败\n'
              f'closed vs blind  p={stat["closed_vs_blind"]["p"]:.2g}', fontsize=11)
axa.axhline(0.25, ls=':', c='gray')
axa.text(3.4, 0.27, '随机', fontsize=8, c='gray', ha='center')

# (b) 延迟 × 补偿
axb = ax[0, 1]
lags = sorted(int(k) for k in R['D_lag'])
nv = [R['D_lag'][str(l)]['naive']['rate'] for l in lags]
pv = [R['D_lag'][str(l)]['pred']['rate'] for l in lags]
axb.plot(lags, nv, 'o-', c='#c0504d', lw=2, label='naive（只用眼睛）')
axb.plot(lags, pv, 's-', c='#2a7fbf', lw=2, label='本体觉补偿（记得自己手往哪动了）')
axb.set_xlabel('渲染延迟（帧）')
axb.set_ylabel('命中率')
axb.set_ylim(-0.05, 1.05)
axb.legend(fontsize=9)
axb.set_title('(b) 延迟 1 帧，纯视觉归零；本体觉把它救回来\n'
              f'lag=1: {hn}/{nD} vs {hp}/{nD}  p={stat["lag1_naive_vs_pred"]["p"]:.2g}', fontsize=11)

# (c) 分辨率
axc = ax[1, 0]
cols_list = sorted([int(k) for k in R['E_res']])
rv = [R['E_res'][str(c)]['rate'] for c in cols_list]
axc.semilogx(cols_list, rv, 'o-', c='#2a7fbf', lw=2)
axc.set_xlabel('画面分辨率（像素列数）')
axc.set_ylabel('命中率')
axc.set_ylim(-0.05, 1.05)
axc.axvspan(0.1, 12, color='#c0504d', alpha=0.10)
axc.text(4.5, 0.5, '崩塌区', fontsize=10, c='#c0504d')
axc.set_title('(c) 分辨率是阈值不是渐变：25 列还能玩，6 列全瞎\n'
              f'25列 vs 6列  p={stat["res25_vs_res6"]["p"]:.2g}', fontsize=11)

# (d) 预算权衡
axd = ax[1, 1]
cmap = {600.0: '#c0504d', 1500.0: '#e08b2a', 3000.0: '#2a7fbf', 6000.0: '#3a8f4f'}
for Tk in ['600.0', '1500.0', '3000.0', '6000.0']:
    row = Rc[Tk]
    ws = sorted(int(k) for k in row)
    ys = [row[str(w)]['rate'] for w in ws]
    peak = max(ws, key=lambda w: row[str(w)]['rate'])
    axd.semilogx(ws, ys, 'o-', c=cmap[float(Tk)], lw=2, label=f'预算 {float(Tk):.0f}（峰值 {peak} 列）')
axd.set_xlabel('每帧渲染多少列（画质）')
axd.set_ylabel('命中率')
axd.set_ylim(-0.05, 1.05)
axd.legend(fontsize=9)
axd.set_title('(d) 画质与帧数抢同一份预算：倒 U，且峰值随预算右移', fontsize=11)

plt.tight_layout()
p = os.path.join(FIG, '095_play_game.png')
plt.savefig(p, dpi=135)
print('\n图已保存:', p)
