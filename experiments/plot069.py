# -*- coding: utf-8 -*-
"""069 结果图"""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'SimHei']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]
        break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False

d69 = json.load(open(os.path.join(ROOT, 'result_069.json'), encoding='utf-8'))
d69b = json.load(open(os.path.join(ROOT, 'result_069b.json'), encoding='utf-8'))
d69c = json.load(open(os.path.join(ROOT, 'result_069c.json'), encoding='utf-8'))

fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
fig.suptitle('069 · 判据核检索结构：时间序是好是坏，取决于检索范围',
             fontsize=14, fontweight='bold')

# ---- (1) P1 三重度量 ----
ax = axes[0, 0]
names = ['bigram', 'unigram', 'jaccard']
labels = ['字符bigram', '字符unigram', '实词Jaccard']
p1 = d69['P1_time_order_redundancy']
adj = [p1[n]['adjacent_mean'] for n in names]
rnd = [p1[n]['random_pair_mean'] for n in names]
shf = [d69['N1_shuffle_items'][n]['shuffled_adjacent_mean'] for n in names]
x = np.arange(3); w = 0.27
ax.bar(x - w, adj, w, label='编号相邻', color='#c0392b')
ax.bar(x, rnd, w, label='随机配对', color='#95a5a6')
ax.bar(x + w, shf, w, label='负对照:条目重排', color='#3498db')
for i, n in enumerate(names):
    ax.text(i - w, adj[i], '%.3f' % adj[i], ha='center', va='bottom', fontsize=8)
    ax.text(i + w, shf[i], '%.3f' % shf[i], ha='center', va='bottom', fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel('相似度')
ax.set_title('① 相邻相似度 vs 随机（三重独立度量一致）\n负对照：重排即塌回随机 → 冗余来自配对本身',
             fontsize=10)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

# ---- (2) 阈值敏感性 ----
ax = axes[0, 1]
ts = d69b['threshold_sensitivity']
q = [str(r['percentile']) for r in ts]
rr = [r['redundancy_rate'] * 100 for r in ts]
th = [r['threshold'] for r in ts]
ax.plot(range(len(ts)), rr, 'o-', color='#c0392b', lw=2, ms=7)
for i, (a, b) in enumerate(zip(rr, th)):
    ax.annotate('%.0f%%\n(θ=%.3f)' % (a, b), (i, a), textcoords='offset points',
                xytext=(0, 9), ha='center', fontsize=8)
ax.set_xticks(range(len(ts)))
ax.set_xticklabels(['p%s' % s for s in q], fontsize=9)
ax.set_ylabel('连续取 50 条的冗余率 (%)')
ax.set_title('② 冗余率强烈依赖阈值：90.9% → 7.4%\n→ P2 的"59%冗余"是阈值 artifact，不可直接引用',
             fontsize=10)
ax.grid(alpha=0.3)

# ---- (3) 配对检验森林图 ----
ax = axes[1, 0]
pa = d69c['A_paired']
ks = ['K5', 'K10', 'K20', 'K50']
ys = np.arange(len(ks))
for i, k in enumerate(ks):
    r = pa[k]
    lo, hi = r['ci95']
    col = '#27ae60' if lo > 0 else ('#c0392b' if hi < 0 else '#7f8c8d')
    ax.plot([lo, hi], [i, i], color=col, lw=3, solid_capstyle='butt')
    ax.plot(r['diff_mean'], i, 'o', color=col, ms=8)
ax.axvline(0, color='k', ls='--', lw=1)
ax.set_yticks(ys); ax.set_yticklabels(ks, fontsize=9)
ax.set_xlabel('语义序召回 − 时间序召回（bootstrap 95% CI）')
ax.set_title('③ 配对检验：小 K 时两者【无显著差异】\n只有 K=50 语义显著更好（CI 全在 0 右侧）',
             fontsize=10)
for i, k in enumerate(ks):
    r = pa[k]
    tag = '显著' if (r['ci95'][0] > 0 or r['ci95'][1] < 0) else '不显著'
    ax.text(0.105, i, tag, fontsize=8, va='center',
            color='#27ae60' if r['ci95'][0] > 0 else '#7f8c8d')
ax.grid(axis='x', alpha=0.3)

# ---- (4) 两个任务方向相反 ----
ax = axes[1, 1]
b = d69c['B_tasks']
tasks = ['T1 前瞻分半\n(用前半覆盖后半)', 'T2 近邻检索\n(取最近10条)']
time_v = [b['T1_time_half_coverage'], b['T2_time_K10']]
rand_v = [b['T1_random_half_mean'], b['T2_random_K10']]
x = np.arange(2); w = 0.32
ax.bar(x - w / 2, time_v, w, label='时间序', color='#c0392b')
ax.bar(x + w / 2, rand_v, w, label='随机基线', color='#95a5a6')
for i in range(2):
    d = time_v[i] - rand_v[i]
    ax.annotate('%+.3f' % d, (i, max(time_v[i], rand_v[i])),
                textcoords='offset points', xytext=(0, 8), ha='center',
                fontsize=10, fontweight='bold',
                color='#27ae60' if d > 0 else '#c0392b')
    ax.text(i - w / 2, time_v[i] / 2, '%.3f' % time_v[i], ha='center',
            va='center', color='w', fontsize=9, fontweight='bold')
    ax.text(i + w / 2, rand_v[i] / 2, '%.3f' % rand_v[i], ha='center',
            va='center', color='w', fontsize=9, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(tasks, fontsize=9)
ax.set_ylabel('召回 / 覆盖度')
ax.set_title('④ 同一份库，两个任务方向【相反】\n时间序：局部近邻=强先验(+0.254)，大块跨期=最差切分(-0.215)',
             fontsize=10)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.95])
out = os.path.join(ROOT, 'fig', '069_retrieval.png')
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, dpi=140, bbox_inches='tight')
print('saved', out)
