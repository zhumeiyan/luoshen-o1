#!/usr/bin/env python3
# 180: 学习人类的目标 —— 目标在不在动
# 判据: 若目标静止 -> 累计数据(更多)必优于近端(更少)
#       若目标在动 -> 老数据成为噪声, 累计 <= 近端
import os, json, random, hashlib
from collections import defaultdict, Counter

SRC = '/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt'
OUT = '/data/workspace/luoshen-o1/experiments/exp180_goal'
os.makedirs(OUT, exist_ok=True)

txt = open(SRC, encoding='utf-8').read()
lines = [l.strip() for l in txt.split('\n') if l.strip()]
txt = '\n'.join(lines)
print('corpus chars', len(txt), 'lines', len(lines))

W = 10
n = len(txt)
S = n // W
wins = [txt[i*S:(i+1)*S] for i in range(W)]
wins[-1] = txt[(W-1)*S:]
print('windows', W, 'size~', S)

K = 3


def train(s):
    m = defaultdict(Counter)
    for i in range(len(s) - K):
        m[s[i:i+K-1]][s[i+K-1]] += 1
    return m


def score(m, t):
    hit = 0
    tot = 0
    for i in range(len(t) - K):
        c = m.get(t[i:i+K-1])
        tot += 1
        if c and c.most_common(1)[0][0] == t[i+K-1]:
            hit += 1
    return hit / tot if tot else 0.0


res = {}

# 1) 陈旧度扫描: 用窗口 p-L 训练, 测窗口 p
stale = {}
for L in range(1, 6):
    accs = []
    for p in range(L, W):
        accs.append(score(train(wins[p-L]), wins[p]))
    stale[L] = sum(accs) / len(accs)
    print('stale L=%d  acc=%.4f  (n=%d)' % (L, stale[L], len(accs)))
res['stale'] = stale

# 2) 四条件对照: 目标窗口 p
# A 近端: 只用 p-1
# B 远端: 只用 0
# C 累计: 用 0..p-1  (数据量最大)
# D 随机: 用一个随机窗口 (等长对照)
random.seed(7)
cond = {}
for name in ['A_near', 'B_far', 'C_cumu', 'D_rand']:
    cond[name] = {}
for L in [1, 2, 3]:
    accA, accB, accC, accD = [], [], [], []
    for p in range(max(L, 2), W):
        t = wins[p]
        accA.append(score(train(wins[p-1]), t))
        accB.append(score(train(wins[0]), t))
        accC.append(score(train(''.join(wins[0:p])), t))
        rw = random.choice([w for w in wins if w is not t and w != wins[p-1] and w != wins[0]])
        accD.append(score(train(rw), t))
    cond['A_near'][L] = sum(accA)/len(accA)
    cond['B_far'][L] = sum(accB)/len(accB)
    cond['C_cumu'][L] = sum(accC)/len(accC)
    cond['D_rand'][L] = sum(accD)/len(accD)
    print('L=%d  A_near=%.4f  B_far=%.4f  C_cumu=%.4f  D_rand=%.4f' % (
        L, cond['A_near'][L], cond['B_far'][L], cond['C_cumu'][L], cond['D_rand'][L]))
res['cond'] = cond

# 3) 累计是否反而不如近端 (关键判据)
key = {}
for L in [1, 2, 3]:
    key['L%d_cumu_minus_near' % L] = cond['C_cumu'][L] - cond['A_near'][L]
    key['L%d_far_over_near' % L] = cond['B_far'][L] / cond['A_near'][L] if cond['A_near'][L] else None
res['key'] = key
print('KEY', json.dumps(key, ensure_ascii=False))

# 4) 目标漂移率: stale 曲线指数拟合
import math
xs = sorted(stale.keys())
ys = [stale[x] for x in xs]
lx = [math.log(x) for x in xs]
ly = [math.log(max(y, 1e-9)) for y in ys]
mx = sum(lx)/len(lx); my = sum(ly)/len(ly)
num = sum((a-mx)*(b-my) for a, b in zip(lx, ly))
den = sum((a-mx)**2 for a in lx)
slope = num/den if den else 0.0
res['drift_loglog_slope'] = slope
print('drift slope(log-log) = %.4f' % slope)

res['corpus_chars'] = len(txt)
res['K'] = K
res['W'] = W

# 5) 打乱对照: 目标静止的零假设 -> 打乱窗口顺序后 A/C 应无差异
sh = list(wins)
random.shuffle(sh)
accA2, accC2 = [], []
for p in range(2, W):
    t = sh[p]
    accA2.append(score(train(sh[p-1]), t))
    accC2.append(score(train(''.join(sh[0:p])), t))
res['shuffled'] = {'A_near': sum(accA2)/len(accA2), 'C_cumu': sum(accC2)/len(accC2)}
print('SHUFFLED  A_near=%.4f  C_cumu=%.4f' % (res['shuffled']['A_near'], res['shuffled']['C_cumu']))

with open(os.path.join(OUT, 'result180.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

# 落盘自检
b = open(os.path.join(OUT, 'result180.json'), 'rb').read()
print('sha', hashlib.sha256(b).hexdigest()[:12], 'bytes', len(b))

# 图
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(xs, ys, 'o-', color='#c0392b', lw=2)
    ax[0].set_xlabel('陈旧度 L (隔了几个窗口)')
    ax[0].set_ylabel('对目标窗口的预测准确率')
    ax[0].set_title('目标漂移: 隔得越远越不准')
    ax[0].grid(alpha=.3)
    names = ['A_near', 'B_far', 'C_cumu', 'D_rand']
    vals = [cond[x][2] for x in names]
    ax[1].bar(names, vals, color=['#27ae60', '#7f8c8d', '#c0392b', '#95a5a6'])
    ax[1].set_ylabel('准确率 (L=2)')
    ax[1].set_title('近端 vs 远端 vs 累计 vs 随机')
    ax[1].grid(alpha=.3, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'render180.png'), dpi=110)
    print('plot ok')
except Exception as e:
    print('plot fail', e)
