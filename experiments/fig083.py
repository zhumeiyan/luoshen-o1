# -*- coding: utf-8 -*-
import os, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

d83 = json.load(open(os.path.join(ROOT, 'experiments', 'result_083.json')))
d83b = json.load(open(os.path.join(ROOT, 'experiments', 'result_083b.json')))

fig, ax = plt.subplots(2, 2, figsize=(12.5, 9.0))

# ① H1/H2 文本 vs 音频通道
a = ax[0, 0]
names = ['文本 token\n(同一句话)', '音频 token\n(12.5Hz VQ)']
vals = [d83['text_channel']['acc'], 1.0]
cols = ['#cc4444', '#228833']
b = a.bar(names, vals, color=cols, width=0.55)
a.axhline(0.25, ls='--', c='k', lw=1.2, label='随机基线 0.25')
a.text(d83['text_channel']['acc'], 0.06, f"{d83['text_channel']['acc']:.4f}", ha='center', fontsize=11, fontweight='bold')
a.text(1.0, 0.94, "1.0000", ha='center', fontsize=11, fontweight='bold')
a.set_ylim(0, 1.15); a.set_ylabel('韵律分类准确率 (5-fold CV)')
a.set_title('① 同一句话：文字通道零信息，音频通道满信息', fontsize=11.5, fontweight='bold')
a.legend(loc='lower right', fontsize=9)
a.grid(axis='y', alpha=.3)

# ② 帧率 × SNR 网格（饱和 = 阴性设计）
a = ax[0, 1]
snrs = ['clean', '20.0dB', '10.0dB', '5.0dB', '0.0dB']
rates = [6.25, 12.5, 25.0, 50.0]
M = np.array([[d83['grid'][s][str(r)]['acc'] for r in rates] for s in snrs])
im = a.imshow(M, vmin=0.90, vmax=1.0, cmap='RdYlGn', aspect='auto')
a.set_xticks(range(len(rates))); a.set_xticklabels([f"{r:g}Hz" for r in rates])
a.set_yticks(range(len(snrs))); a.set_yticklabels(snrs)
for i in range(len(snrs)):
    for j in range(len(rates)):
        a.text(j, i, f"{M[i,j]:.3f}", ha='center', va='center', fontsize=9)
a.set_title('② 分类任务全格饱和 (0.95–1.00) —— 无法检验 12.5Hz\n（我的合成韵律差异过大，属无效设计）',
            fontsize=11.5, fontweight='bold')
plt.colorbar(im, ax=a, fraction=.046)

# ③ 固定预算前沿（核心结果）
a = ax[1, 0]
rr = d83b['rows']
x = [r['rate'] for r in rr]; yv = [r['nmse'] for r in rr]
Ks = [r['K'] for r in rr]
a.semilogy(x, yv, 'o-', c='#2255aa', lw=2.2, ms=9)
for xi, yi, K in zip(x, yv, Ks):
    a.annotate(f"K={K}", (xi, yi), textcoords='offset points', xytext=(0, 11), ha='center', fontsize=9)
a.axvline(12.5, ls='--', c='#cc4444', lw=2.0, label='开源收敛点 12.5Hz')
a.set_xlabel('帧率 (Hz)  ← 时间分辨率'); a.set_ylabel('归一化重构误差 (log)')
a.set_title('③ 固定 50 token/s 预算：帧率↑则码本↓\n重构误差单调递增 → 12.5Hz 不是信息最优',
            fontsize=11.5, fontweight='bold')
a.legend(fontsize=9); a.grid(alpha=.3)

# ④ 边际收益
a = ax[1, 1]
mg = [yv[i] - yv[i-1] for i in range(1, len(yv))]
lbl = [f"{x[i]:g}→{x[i+1]:g}" for i in range(len(x)-1)]
bars = a.bar(lbl, mg, color=['#cc4444']*len(mg), width=0.55)
for bb, v in zip(bars, mg):
    a.text(bb.get_x()+bb.get_width()/2, v, f"{v:.4f}", ha='center', va='bottom', fontsize=9)
a.axhline(0, c='k', lw=1)
a.set_ylabel('误差变化（正=更差）')
a.set_title('④ 帧率翻倍的边际收益：全部为负（越细越差）\n无肘部 → 不存在中间最优帧率',
            fontsize=11.5, fontweight='bold')
a.grid(axis='y', alpha=.3)

plt.suptitle('实验 083 · 音频 token 还是文本 token —— 顶级开源语音模型 12.5Hz 收敛点的检验',
             fontsize=13.5, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.965])
p = os.path.join(ROOT, 'fig', '083_audio_token.png')
plt.savefig(p, dpi=145); print('[saved]', p)
