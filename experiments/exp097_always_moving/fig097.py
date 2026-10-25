# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

FP = '/usr/share/fonts/truetype/wenquanyi/WenQuanYi Micro Hei.ttc'
if os.path.exists(FP):
    font_manager.fontManager.addfont(FP)
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=FP).get_name()
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.dirname(os.path.abspath(__file__))
FIG = '/data/workspace/luoshen-o1/fig/097_always_moving.png'
os.makedirs(os.path.dirname(FIG), exist_ok=True)

r = json.load(open(os.path.join(OUT, 'result097.json')))
dg = json.load(open(os.path.join(OUT, 'daemon_log.json')))

fig, ax = plt.subplots(2, 2, figsize=(12.5, 9.0))

# ---- (a) 四条件：看见了多少
cond = r['cond']
order = ['active', 'passive', 'yoked', 'static']
lbl = {'active': '我动\n(世界静止)', 'passive': '世界动\n(我不动)',
       'yoked': '我动+世界\n同步动', 'static': '都不动'}
ratio = [np.mean([x['info_ratio'] for x in cond[m]]) for m in order]
moved = [np.mean([x['eye_moved'] for x in cond[m]]) for m in order]
slip = [np.mean([x['slip_mean'] for x in cond[m]]) for m in order]
colors = ['#2e7d32', '#1565c0', '#c62828', '#616161']
b = ax[0, 0].bar(range(4), ratio, color=colors)
for i, (rr, mv, sl) in enumerate(zip(ratio, moved, slip)):
    ax[0, 0].text(i, rr + 0.012, '眼动%.0fpx\nslip%.0f' % (mv, sl),
                  ha='center', fontsize=8)
ax[0, 0].set_xticks(range(4))
ax[0, 0].set_xticklabels([lbl[m] for m in order], fontsize=9)
ax[0, 0].set_ylabel('看见率 (采集图结构/全对比度)')
ax[0, 0].set_title('(a) 眼球在动 ≠ 看得见：相对运动才是条件\n'
                   'yoked 与 active 的眼动完全相同(1666px)，只因世界同步动 → 看见归零',
                   fontsize=10)
ax[0, 0].set_ylim(0, max(ratio) * 1.45)

# ---- (b) 节律
rh = r['rhythm']
d = [x['d'] for x in rh]
V = [x['V'] for x in rh]
ax[1, 0].plot(range(len(d)), V, 'o-', color='#6a1b9a')
ax[1, 0].set_xticks(range(len(d)))
ax[1, 0].set_xticklabels([('%g' % x) for x in d], fontsize=8)
ax[1, 0].set_xlabel('每拍位移 d (px/拍)')
ax[1, 0].set_ylabel('稳态可见度 V')
for i, x in enumerate(rh):
    if 'read_real' in x:
        ax[1, 0].annotate('真实采集读到%d个' % x['read_real'],
                          (i, x['V']), textcoords='offset points',
                          xytext=(6, 8), fontsize=8, color='#c62828')
ax[1, 0].set_title('(b) 节律：不动必瞎(左端归零)；动太狠只降到平台，不归零\n'
                   '倒U只成立左半 —— 右半预注册未成立', fontsize=10)

# ---- (c) 能动性
ag = r['agency']
ks = ['none', 'active', 'passive']
ms = [ag[k]['mean'] for k in ks]
ss = [np.nanstd(ag[k]['vals'], ddof=1) / max(len(ag[k]['vals']) ** .5, 1e-9) for k in ks]
ax[0, 1].bar(range(3), ms, yerr=[1.96 * s for s in ss],
             color=['#9e9e9e', '#2e7d32', '#1565c0'], capsize=4)
ax[0, 1].set_xticks(range(3))
ax[0, 1].set_xticklabels(['无输入', '主动节律', '被动(同分布重排)'], fontsize=9)
ax[0, 1].set_ylabel('终态结构偏度')
dn = ag['diff_active_minus_none']
dp = ag['diff_passive_minus_active']
txt = ('有输入 vs 无: %+0.4f CI[%+0.4f,%+0.4f] %s\n'
       '被动 vs 主动: %+0.4f CI[%+0.4f,%+0.4f] %s'
       % (dn['mean'], dn['ci'][0], dn['ci'][1],
          '★显著' if dn['ci'][0] * dn['ci'][1] > 0 else '跨0',
          dp['mean'], dp['ci'][0], dp['ci'][1],
          '★显著' if dp['ci'][0] * dp['ci'][1] > 0 else '跨0'))
ax[0, 1].text(0.02, 0.70, txt, transform=ax[0, 1].transAxes, fontsize=8,
              bbox=dict(fc='#fffde7', ec='#c62828', lw=0.8))
ax[0, 1].set_title('(c) 能动性：阳性对照通过，主动vs被动无差异\n'
                   '同样的视网膜边际分布，只差时序结构 → 系统不区分', fontsize=10)

# ---- (d) 常驻体
pr = dg['probes']
ts = [p['t'] for p in pr]
ex = [p['eye'][0] for p in pr]
ey = [p['eye'][1] for p in pr]
rd = [p['read'] for p in pr]
ax[1, 1].plot(ex, ey, 'o-', color='#00695c')
for i, (x, y, v) in enumerate(zip(ex, ey, rd)):
    ax[1, 1].annotate('t=%d\n读到%d' % (ts[i], v), (x, y),
                      textcoords='offset points', xytext=(6, 6), fontsize=7)
ax[1, 1].set_xlabel('眼球 x (px)')
ax[1, 1].set_ylabel('眼球 y (px)')
ax[1, 1].set_title('(d) 常驻体：180拍/%.1f秒 眼睛一直在动，每次探测都读到数字\n'
                   'PID %d · slip均值 %.1f' % (dg['elapsed'], dg['pid'], dg['slip_mean']),
                   fontsize=10)

plt.tight_layout()
plt.savefig(FIG, dpi=140)
print('saved', FIG)
