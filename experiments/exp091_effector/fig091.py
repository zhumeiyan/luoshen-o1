# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
          '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f); break
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

S = json.load(open('scan091.json'))
H5 = json.load(open('handeye5_n28.json'))
KB = json.load(open('mouse_result.json'))

fig, ax = plt.subplots(2, 2, figsize=(13, 9))

# (1) 返回效率阈值
A = S['A']
ax[0,0].plot([r['eta'] for r in A], [r['acc'] for r in A], 'o-', lw=2, color='#1f6feb')
ax[0,0].set_xscale('log'); ax[0,0].set_ylim(-0.05, 1.05)
ax[0,0].set_xlabel('返回效率 eta（光回到传感器的比例）')
ax[0,0].set_ylabel('位移测量正确率')
ax[0,0].set_title('① 玻璃上为什么不动：低于阈值即归零')
ax[0,0].axhline(0.5, color='gray', ls='--', lw=1)
ax[0,0].grid(alpha=.3)

# (2) 帧间位移上限 + LED 救援
B = S['B']
ax[0,1].bar([r['d'] for r in B], [r['acc'] for r in B], color='#2da44e')
ax[0,1].axvline(9.5, color='red', ls='--', lw=2, label='窗口可测上限 ±9')
ax[0,1].set_xlabel('帧间真实位移（像素）'); ax[0,1].set_ylabel('正确率')
ax[0,1].set_title('② 甩太快就丢帧：超过窗口一半即失配')
ax[0,1].legend(fontsize=8); ax[0,1].grid(alpha=.3, axis='y')

C = S['C']
ax2 = ax[0,1].twinx()
ax2.plot([r['led'] for r in C], [r['acc'] for r in C], 's--', color='#cf222e', lw=2)
ax2.set_ylabel('提高照明后玻璃的恢复率', color='#cf222e')
ax2.set_ylim(-0.05, 1.05)

# (3) 手 vs 眼：偏度
order = ['base', 'eye', 'h_bias', 'h_rand']
lbl = ['无误差', '眼噪\n(看错)', '手·系统性偏差\n(总偏同一边)', '手·每拍随机\n(不可预测)']
cols = ['#8c959f', '#1f6feb', '#d29922', '#cf222e']
vals = [H5['cells'][m]['skew'] for m in order]
ax[1,0].bar(lbl, vals, color=cols)
ax[1,0].set_ylabel('内在结构偏度')
ax[1,0].set_title('③ 不是"眼比手重要"，是"不可预测才重要"')
ax[1,0].grid(alpha=.3, axis='y')
for i, v in enumerate(vals):
    ax[1,0].text(i, v + .01, f'{v:.3f}', ha='center', fontsize=9)

# (4) 中介变量：arrival 翻转率
flips = [H5['cells'][m]['flip'] for m in order]
ax[1,1].bar(lbl, flips, color=cols)
ax[1,1].set_ylabel('arrival 翻转次数（不可预测性）')
ax[1,1].set_title('④ 真正的中介：可预测误差不翻转，不可预测才翻转')
ax[1,1].grid(alpha=.3, axis='y')
for i, v in enumerate(flips):
    ax[1,1].text(i, v + 3, f'{v:.0f}', ha='center', fontsize=9)

plt.tight_layout()
out = '/data/workspace/luoshen-o1/fig/091_effector.png'
plt.savefig(out, dpi=130)
print('saved', out)
print('KB/MOUSE match:', KB.get('match'), 'xs=', KB.get('xs'))
