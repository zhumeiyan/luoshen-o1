# -*- coding: utf-8 -*-
"""128 结果图：外部平台基线对照 Avida vs Life5"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
          '/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc']:
    try:
        font_manager.fontManager.addfont(f)
    except Exception:
        pass
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

D = '/data/workspace/luoshen-o1/experiments/exp128_avida/'
B = json.load(open(D + 'stageB_result.json'))
C = json.load(open(D + 'stageC_result.json'))

fig, ax = plt.subplots(2, 3, figsize=(16, 9))
fig.suptitle('128 · 外部平台基线对照：Avida(演化) vs Luoshen Life5(学习) — 同一断供协议',
             fontsize=13, fontweight='bold')

# ---- 1 Life5 四方案：学到 fg + 断供存活 ----
a = ax[0, 0]
sc = ['practice_closed', 'practice_open', 'no_practice', 'variation']
lab = ['相倚练习', '相继不倚', '只输液', '随机变异']
fgv = [B['life5'][s]['fg'] for s in sv] if False else [B['life5'][s]['fg'] for s in sc]
alv = [B['life5'][s]['survive'] for s in sc]
x = np.arange(4)
a.bar(x - 0.2, fgv, 0.4, label='学到 fg', color='#4C72B0')
a.bar(x + 0.2, alv, 0.4, label='断供存活率', color='#55A868')
a.set_xticks(x); a.set_xticklabels(lab, fontsize=9)
a.set_title('① Life5：学到 fg 与断供存活', fontsize=10)
a.legend(fontsize=8); a.set_ylim(0, 1.15)
for i, (f_, s_) in enumerate(zip(fgv, alv)):
    a.text(i - 0.2, f_ + 0.03, f'{f_:.3f}', ha='center', fontsize=8)
    a.text(i + 0.2, s_ + 0.03, f'{s_:.2f}', ha='center', fontsize=8)

# ---- 2 Avida 各 seed 自给获得率（方差）----
a = ax[0, 1]
seeds = [r['seed'] for r in C['avida_state']]
rates = [r['n_task'] / r['n'] for r in C['avida_state']]
a.bar(seeds, rates, color='#C44E52')
a.set_title('② Avida：自给能力获得率（seed 间方差极大）', fontsize=10)
a.set_xlabel('seed'); a.set_ylabel('获得自给个体占比')
a.set_ylim(0, 0.4)
a.axhline(np.mean(rates), color='k', ls='--', lw=1,
          label=f'均值 {np.mean(rates):.3f}')
a.legend(fontsize=8)
for s_, r_ in zip(seeds, rates):
    a.text(s_, r_ + 0.01, f'{r_:.3f}', ha='center', fontsize=8)

# ---- 3 断供后状态分解 ----
a = ax[0, 2]
t = C['avida_total']
cats = ['获得\n自给', '断供后\n有能量', '有自给\n且能繁殖', '有自给\n但已废']
vals = [t['n_task'], t['n_energy'], t['n_task_and_replicate'], t['n_task_not_replicate']]
bars = a.bar(cats, vals, color=['#4C72B0', '#55A868', '#DD8452', '#C44E52'])
a.set_title('③ Avida 断供后个体状态（N=200）', fontsize=10)
a.set_ylabel('个体数')
for b_, v_ in zip(bars, vals):
    a.text(b_.get_x() + b_.get_width() / 2, v_ + 0.3, str(v_), ha='center', fontsize=9)

# ---- 4 核心对照 ----
a = ax[1, 0]
labels = ['Avida\n(演化获得自给后)', 'Life5\n(相倚学会 fg 后)']
maintain = [t['n_task_and_replicate'] / t['n'], B['life5']['practice_closed']['survive']]
bars = a.bar(labels, maintain, color=['#C44E52', '#55A868'])
a.set_ylim(0, 1.15); a.set_ylabel('断供后仍维持的比例')
a.set_title('④ 核心对照：获得自给后还能不能维持', fontsize=10)
for b_, v_ in zip(bars, maintain):
    a.text(b_.get_x() + b_.get_width() / 2, v_ + 0.02, f'{v_:.3f}',
           ha='center', fontsize=11, fontweight='bold')

# ---- 5 可证伪对照 ----
a = ax[1, 1]
ctrl = C['controls']
names = ['Avida\n阴性 mut=0', 'Avida\n阳性 给任务', 'Life5\n阴性 fg=0', 'Life5\n阳性 fg=.15']
got = [ctrl['avida']['neg_mut0_tasks'] / 40,
       ctrl['avida']['pos_given_task_energy'] / 40,
       ctrl['life5']['neg_fg0'] / 16, ctrl['life5']['pos_fg015'] / 16]
exp = [0.0, 1.0, 0.0, 1.0]
x = np.arange(4)
a.bar(x - 0.2, got, 0.4, label='实测', color='#4C72B0')
a.bar(x + 0.2, exp, 0.4, label='理论预期', color='#999999')
a.set_xticks(x); a.set_xticklabels(names, fontsize=8)
a.set_title('⑤ 可证伪对照（阴/阳）', fontsize=10)
a.legend(fontsize=8); a.set_ylim(0, 1.2)

# ---- 6 文字结论 ----
a = ax[1, 2]
a.axis('off')
txt = (
    "对照结论\n\n"
    f"· Avida 获得自给：{t['n_task']}/{t['n']} = {t['n_task']/t['n']:.1%}\n"
    f"  但其中能繁殖者：{t['n_task_and_replicate']}/{t['n']} = 0%\n"
    f"  → 获得者与丧失繁殖 100% 重叠\n\n"
    f"· Life5 相倚练习：fg={B['life5']['practice_closed']['fg']:.4f}\n"
    f"  断供存活 {B['life5']['practice_closed']['survive']:.0%} (16/16)\n\n"
    f"· Life5 相继不倚：fg={B['life5']['practice_open']['fg']:.4f}\n"
    f"  断供存活 {B['life5']['practice_open']['survive']:.0%} (0/16)\n\n"
    "共同点：能否自给取决于\n世界是否【相倚】回应我的行动"
)
a.text(0.02, 0.98, txt, va='top', fontsize=9.5,
       bbox=dict(boxstyle='round', fc='#FFF8E7', ec='#DD8452'))

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('/data/workspace/luoshen-o1/fig/128_avida_baseline.png', dpi=110)
print('saved fig/128_avida_baseline.png')
