import sys, numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue108 import build, sim, sim_row, sim_max

items, X = build()
N = X.shape[0]
print('轮数', len(items), ' 句子数', N)
rng = np.random.default_rng(0)
sub = [items[i] for i in rng.choice(len(items), 600, replace=False)]

rp = np.array([sim(X, it['gold'], it['prev']) for it in sub])
rf = np.array([max([sim(X, it['gold'], f) for f in it['far']], default=0.0)
               for it in sub])
print('gold↔上一句   均值 %.4f 中位 %.4f' % (rp.mean(), np.median(rp)))
print('gold↔更早话题 均值 %.4f 中位 %.4f' % (rf.mean(), np.median(rf)))
print()
print('★ h 扫描（h=0 只接上一句 / h=1 只跟更早话题）候选10句')
for h in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
    hit = 0
    rg = np.random.default_rng(7)
    for it in sub:
        cands = [it['gold']] + [int(rg.integers(0, N)) for _ in range(9)]
        sp = sim_row(X, cands, it['prev'])
        sf = sim_max(X, cands, it['far'])
        sc = h * sf + (1 - h) * sp
        hit += int(np.argmax(sc)) == 0
    print('  h=%.1f  挑中真人 %.3f' % (h, hit / len(sub)))
