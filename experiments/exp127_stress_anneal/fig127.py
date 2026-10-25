# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = "/data/workspace/luoshen-o1/experiments/exp127_stress_anneal"
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
          "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=p).get_name()
        break
plt.rcParams['axes.unicode_minus'] = False

B = json.load(open(OUT + "/result127B.json"))
C = json.load(open(OUT + "/result127C.json"))
D = json.load(open(OUT + "/result127D.json"))

fig, ax = plt.subplots(2, 3, figsize=(18, 10))

# 1 应力扫描
a = ax[0, 0]
for nm, col, mk in [('S1 失血', '#c0392b', 'o'), ('S2 发烧', '#2980b9', 's'), ('S3 老化', '#27ae60', '^')]:
    rows = B[nm]
    xs = np.arange(len(rows))
    a.plot(xs, [r['alive'] for r in rows], mk + '-', color=col, label=nm, lw=2)
a.set_xticks(range(8))
a.set_xticklabels([f"{r['level']:.3g}" for r in B['S1 失血']], fontsize=8)
a.axhline(0.5, ls='--', c='gray', lw=1)
a.set_title("① 应力扫描：只有发烧是陡峭临界", fontsize=12)
a.set_xlabel("档位序号（三维度各自从弱到强）", fontsize=9)
a.set_ylabel("撤除供给后存活率", fontsize=10)
a.legend(fontsize=8); a.grid(alpha=.3)

# 2 P2 学习律归一化
a = ax[0, 1]
nz = [float(k) for k in B['P2'].keys()]
orig = [B['P2'][k][0] for k in B['P2']]
norm = [B['P2'][k][1] for k in B['P2']]
a.semilogx(nz, orig, 'o-', c='#c0392b', label='原版（协方差）', lw=2)
a.semilogx(nz, norm, 's-', c='#27ae60', label='归一版（相关系数）', lw=2)
a.set_title("② 尺度泄漏：噪声越大学得越多是假的", fontsize=12)
a.set_xlabel("世界噪声", fontsize=10); a.set_ylabel("学到的 fg", fontsize=10)
a.legend(fontsize=9); a.grid(alpha=.3)
a.annotate('尺度泄漏', xy=(16, orig[-1]), xytext=(2, 0.6), fontsize=9, color='#c0392b',
           arrowprops=dict(arrowstyle='->', color='#c0392b'))

# 3 退火：fg
a = ax[0, 2]
ks = ['cool', 'constant', 'slow', 'fast', 'quench']
lb = ['常温\n(无高温)', '高温恒温', '慢退火', '快退火', '淬火']
an = C['anneal']
v = [an[k]['fg'] for k in ks]
bars = a.bar(lb, v, color=['#7f8c8d', '#c0392b', '#27ae60', '#e67e22', '#8e44ad'])
for b_, vv in zip(bars, v):
    a.text(b_.get_x() + b_.get_width() / 2, vv, f"{vv:.4f}", ha='center', va='bottom', fontsize=9)
a.set_title("③ 退火后学到多少：高温恒温最大（但是虚高）", fontsize=12)
a.set_ylabel("学到的 fg", fontsize=10); a.grid(alpha=.3, axis='y')

# 4 退火：漂移（稳定性）
a = ax[1, 0]
v = [an[k]['drift'] for k in ks]
bars = a.bar(lb, v, color=['#7f8c8d', '#c0392b', '#27ae60', '#e67e22', '#8e44ad'])
a.set_yscale('log')
for b_, vv in zip(bars, v):
    a.text(b_.get_x() + b_.get_width() / 2, vv, f"{vv:.5f}", ha='center', va='bottom', fontsize=8)
a.set_title("④ 稳定性：退火后漂移小 8 倍（退火的价值是稳不是大）", fontsize=12)
a.set_ylabel("最后300拍 |Δfg|（对数轴）", fontsize=10); a.grid(alpha=.3, axis='y')

# 5 退火速率剂量
a = ax[1, 1]
d = D['anneal_dose']
x = [r['ratio'] for r in d]
a.semilogx(x, [r['fg'] for r in d], 'o-', c='#2980b9', label='学到 fg', lw=2)
a2 = a.twinx()
a2.semilogx(x, [r['drift'] for r in d], 's--', c='#c0392b', label='漂移', lw=2)
a.set_title("⑤ 降温时长剂量：单调权衡，无最优点", fontsize=12)
a.set_xlabel("降温时间常数 / 训练总长", fontsize=10)
a.set_ylabel("学到 fg", fontsize=10); a2.set_ylabel("漂移", fontsize=10)
a.legend(loc=2, fontsize=9); a2.legend(loc=4, fontsize=9); a.grid(alpha=.3)

# 6 续学配对：好世界 vs 坏世界
a = ax[1, 2]
cp = D['continue_pair']
kk = ['cool', 'constant', 'slow', 'quench']
g = [cp[k]['dgood'] for k in kk]
b_ = [cp[k]['dbad'] for k in kk]
x = np.arange(len(kk)); w = 0.36
a.bar(x - w / 2, g, w, label='好世界续学 Δfg', color='#27ae60')
a.bar(x + w / 2, b_, w, label='坏世界续学 Δfg', color='#c0392b')
a.set_yscale('symlog', linthresh=1e-4)
a.set_xticks(x); a.set_xticklabels(kk, fontsize=9)
a.set_title("⑥ 配对对照：坏世界教不了东西（Δ≈0）", fontsize=12)
a.legend(fontsize=9); a.grid(alpha=.3, axis='y')

plt.tight_layout()
plt.savefig(OUT + "/fig127.png", dpi=110)
plt.savefig("/data/workspace/luoshen-o1/fig/127_stress_anneal.png", dpi=110)
print("saved fig127.png")
