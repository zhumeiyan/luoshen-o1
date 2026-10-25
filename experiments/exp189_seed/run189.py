# -*- coding: utf-8 -*-
"""
189: 种子问题 —— 提升能力是"激发种子"还是"线性扩容"？

种子 = 用户的话（高密度，我的尺）
土壤 = 判据核（大量、低密度、异质）

判据：如果能力提升是"激发种子"而非"扩容"，则
  种子与土壤之间应存在【交互效应】——不是简单相加。
  - 交互 > 0 : 超加性，土壤真的帮种子展开（种子需要土壤）
  - 交互 < 0 : 稀释，异质土壤盖住了种子的分布

三测：
  A 交互项      s x t 因子网格
  B 发芽阈值    固定种子，细扫土壤量（非单调？适量促发芽，过量稀释）
  C 临界质量    固定土壤，细扫种子量（S 形？种子需要到一定量才发芽）
"""
import json, os, re
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BASE = '/data/workspace/luoshen-o1'
SEED_PATH = BASE + '/experiments/exp180_record/u_side_full.txt'
SOIL_PATH = BASE + '/evidence/失败模式库/判据核.md'
OUT = BASE + '/experiments/exp189_seed'
os.makedirs(OUT, exist_ok=True)

# ---------- 加载 ----------
raw = open(SEED_PATH, encoding='utf-8').read()
soil = open(SOIL_PATH, encoding='utf-8').read()

lines = raw.split('\n')
clean = []
for ln in lines:
    s = ln.strip()
    if not s:
        continue
    if s.startswith('#') or s.startswith('==') or s.startswith('['):
        continue
    s = re.sub(r'^\[?U0\d+\]?\s*', '', s)   # 剥离编号前缀
    clean.append(s)
seed = '\n'.join(clean)

print('SEED head:', repr(seed[:150]))
print('SOIL head:', repr(soil[:150]))
print('len seed', len(seed), '| len soil', len(soil))

# ---------- 划分 ----------
n = len(seed)
tr_seed = seed[:int(n * 0.8)]
test = seed[int(n * 0.8):]
Ns = len(tr_seed)
print('train_seed', Ns, '| test', len(test))

# 固定词表（179号教训：词表随数据变化会造出假趋势）
VOCAB = sorted(set(seed) | set(soil))
VIDX = {c: i for i, c in enumerate(VOCAB)}
V = len(VOCAB)


def build(text, k):
    m = defaultdict(lambda: defaultdict(int))
    for i in range(len(text) - k):
        m[text[i:i + k]][text[i + k]] += 1
    return m


def acc_of(m, k):
    c = t = 0
    for i in range(len(test) - k):
        ctx = test[i:i + k]; nx = test[i + k]
        if ctx in m:
            p = max(m[ctx], key=m[ctx].get)
            if p == nx:
                c += 1
        t += 1
    return c / t if t else 0.0


def cov_of(m, k):
    t = seen = 0
    for i in range(len(test) - k):
        if test[i:i + k] in m:
            seen += 1
        t += 1
    return seen / t if t else 0.0


def bits_of(m, k):
    """固定词表 + 加一平滑的交叉熵（bits/字符），越低越好"""
    tot = 0.0; cnt = 0
    for i in range(len(test) - k):
        ctx = test[i:i + k]; nx = test[i + k]
        d = m.get(ctx)
        if d is None:
            p = 1.0 / V                     # 未见 context：均匀
        else:
            s = sum(d.values()) + V         # 加一平滑
            p = (d.get(nx, 0) + 1.0) / s
        tot += -np.log2(p); cnt += 1
    return tot / cnt if cnt else float('nan')


# ================= A 交互项：s x t 因子网格 =================
print('\n=== A 因子网格 ===')
svals = [0, 0.25, 0.5, 0.75, 1.0]
tvals = [0, 0.5, 1, 2, 4]
grid = {}       # grid[k][s][t] = acc
gridb = {}      # bits
gridc = {}      # coverage

for k in [1, 2, 3]:
    grid[k] = {}; gridb[k] = {}; gridc[k] = {}
    for s in svals:
        grid[k][s] = {}; gridb[k][s] = {}; gridc[k][s] = {}
        for t in tvals:
            txt = tr_seed[:int(Ns * s)] + soil[:int(Ns * t)]
            m = build(txt, k)
            a = acc_of(m, k)
            grid[k][s][t] = a
            gridb[k][s][t] = bits_of(m, k)
            gridc[k][s][t] = cov_of(m, k)
            print(f'k={k} s={s} t={t}  acc={a:.4f} bits={gridb[k][s][t]:.4f} cov={gridc[k][s][t]:.4f}')

# 交互项（k=2 主，k=1/3 稳健）
inter = {}
for k in [1, 2, 3]:
    a00 = grid[k][0.0][0]
    a10 = grid[k][1.0][0]        # 只有种子
    a01 = grid[k][0.0][1]        # 只有土壤
    a11 = grid[k][1.0][1]        # 种子+土壤（等量）
    e_seed = a10 - a00
    e_soil = a01 - a00
    e_both = a11 - a00
    inter[k] = {
        'acc_seed_only': a10, 'acc_soil_only': a01, 'acc_both': a11, 'acc_none': a00,
        'E_seed': e_seed, 'E_soil': e_soil, 'E_both': e_both,
        'interaction': e_both - e_seed - e_soil,
        'soil_marginal_given_seed': a11 - a10,   # 有种子时，加土壤是帮忙还是稀释
    }
print('\n=== 交互项 ===')
for k, v in inter.items():
    print(f'k={k}: seed={v["acc_seed_only"]:.4f} soil={v["acc_soil_only"]:.4f} '
          f'both={v["acc_both"]:.4f} | interaction={v["interaction"]:+.4f} '
          f'| soil|seed={v["soil_marginal_given_seed"]:+.4f}')

# ================= B 发芽阈值：固定种子，细扫土壤 =================
print('\n=== B 发芽阈值（s=1.0） ===')
tfine = [0, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8]
germ = {}
for k in [2]:
    germ[k] = []
    for t in tfine:
        txt = tr_seed + soil[:int(Ns * t)]
        m = build(txt, k)
        a = acc_of(m, k)
        germ[k].append({'t': t, 'acc': a, 'bits': bits_of(m, k), 'cov': cov_of(m, k)})
        print(f't={t}: acc={a:.4f} cov={germ[k][-1]["cov"]:.4f}')

# 一阶差分找最大跳变（阶梯检测）
accs = [g['acc'] for g in germ[2]]
diffs = [accs[i + 1] - accs[i] for i in range(len(accs) - 1)]
maxjump = int(np.argmax(diffs)) if diffs else -1
print('土壤扫描 acc 序列:', [round(a, 4) for a in accs])
print('最大正跳变位置 idx=', maxjump, ' 幅度=', diffs[maxjump] if maxjump >= 0 else None)
peak_idx = int(np.argmax(accs))
print('峰值 t =', tfine[peak_idx], ' acc =', accs[peak_idx])

# ================= C 临界质量：固定土壤，细扫种子 =================
print('\n=== C 种子临界质量（t=0.5） ===')
sfine = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
T_FIX = 0.5
crit = []
for s in sfine:
    txt = tr_seed[:int(Ns * s)] + soil[:int(Ns * T_FIX)]
    m = build(txt, 2)
    a = acc_of(m, 2)
    crit.append({'s': s, 'acc': a, 'cov': cov_of(m, 2)})
    print(f's={s}: acc={a:.4f} cov={crit[-1]["cov"]:.4f}')

# ================= 图 =================
fig, axes = plt.subplots(2, 2, figsize=(13, 9))

# A 热力图
ax = axes[0, 0]
M = np.array([[grid[2][s][t] for t in tvals] for s in svals])
im = ax.imshow(M, cmap='viridis', origin='lower', aspect='auto')
ax.set_xticks(range(len(tvals))); ax.set_xticklabels([f'{t}x' for t in tvals])
ax.set_yticks(range(len(svals))); ax.set_yticklabels([f'{int(s*100)}%' for s in svals])
ax.set_xlabel('土壤量（×种子训练量）'); ax.set_ylabel('种子量')
ax.set_title('A 种子 × 土壤（k=2, top-1）')
for i in range(len(svals)):
    for j in range(len(tvals)):
        ax.text(j, i, f'{M[i,j]:.3f}', ha='center', va='center', color='w', fontsize=8)
plt.colorbar(im, ax=ax)

# A2 边际效应：有种子时加土壤
ax = axes[0, 1]
ax.plot(tvals, [grid[2][1.0][t] for t in tvals], 'o-', color='crimson', label='种子全量 s=1.0')
ax.plot(tvals, [grid[2][0.0][t] for t in tvals], 's--', color='gray', label='无种子 s=0')
ax.plot(tvals, [grid[2][1.0][0]] * len(tvals), ':', color='black', label='纯种子基线')
ax.set_xlabel('土壤量（×种子训练量）'); ax.set_ylabel('top-1 acc')
ax.set_title(f'B 土壤的边际作用（交互={inter[2]["interaction"]:+.4f}）')
ax.legend(fontsize=8); ax.grid(alpha=.3)

# B 细扫发芽
ax = axes[1, 0]
ax.plot(tfine, accs, 'o-', color='darkgreen')
ax.axhline(accs[0], ls=':', color='black', label='无土壤基线')
ax.axvline(tfine[peak_idx], ls='--', color='red', alpha=.6, label=f'峰值 t={tfine[peak_idx]}')
ax.set_xlabel('土壤量（×种子训练量）'); ax.set_ylabel('top-1 acc')
ax.set_title('B′ 发芽阈值扫描（s=1.0）')
ax.legend(fontsize=8); ax.grid(alpha=.3)

# C 临界质量
ax = axes[1, 1]
ax.plot([c['s'] for c in crit], [c['acc'] for c in crit], 'o-', color='darkorange')
ax.plot([c['s'] for c in crit], [c['cov'] for c in crit], 's--', color='steelblue', label='覆盖率')
ax.set_xlabel('种子量（占种子训练语料比例）'); ax.set_ylabel('acc / coverage')
ax.set_title('C 种子临界质量（t=0.5）')
ax.legend(fontsize=8); ax.grid(alpha=.3)

plt.tight_layout()
plt.savefig(OUT + '/render189.png', dpi=110)
print('\nsaved', OUT + '/render189.png')

# ================= JSON =================
res = {
    'corpus': {'seed_chars': len(seed), 'soil_chars': len(soil),
               'train_seed_chars': Ns, 'test_chars': len(test), 'vocab': V},
    'grid_acc': {str(k): {str(s): {str(t): grid[k][s][t] for t in tvals} for s in svals} for k in [1, 2, 3]},
    'grid_bits': {str(k): {str(s): {str(t): gridb[k][s][t] for t in tvals} for s in svals} for k in [1, 2, 3]},
    'grid_cov': {str(k): {str(s): {str(t): gridc[k][s][t] for t in tvals} for s in svals} for k in [1, 2, 3]},
    'interaction': {str(k): inter[k] for k in [1, 2, 3]},
    'germination_scan': {str(k): germ[k] for k in germ},
    'germination_peak_t': tfine[peak_idx],
    'germination_peak_acc': accs[peak_idx],
    'critical_mass_scan': crit,
    'max_jump_idx': maxjump,
    'note': '土壤=判据核.md(异质); 交互<0 表示异质土壤稀释种子分布',
}
json.dump(res, open(OUT + '/result189.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print('saved', OUT + '/result189.json')
