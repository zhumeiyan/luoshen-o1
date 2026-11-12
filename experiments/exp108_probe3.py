import sys, numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue108 import build, sim, sim_row, sim_max

items, X = build()
N = X.shape[0]
sub = [items[i] for i in np.random.default_rng(0).choice(len(items), 500, replace=False)]
GT = np.array([sim(X, it['gold'], it['prev']) for it in sub])
print('真值：真人回应↔上一句 均值 %.4f 中位 %.4f' % (GT.mean(), np.median(GT)))
print()

print('★ 打分 = h·话题 - |接上一句 - d|   （d = 她认为「接多少刚刚好」）')
for h in [0.0, 0.3, 0.6, 1.0]:
    row = []
    for d in [0.0, 0.03, 0.066, 0.12, 0.25, 0.5, 1.0]:
        hit = 0
        rg = np.random.default_rng(7)
        for it in sub:
            sp_all = np.asarray((X @ X[it['prev']].T).todense()).ravel()
            sp_all[it['gold']] = -1
            dec = list(np.argsort(-sp_all)[:2])          # 含 prev 原话等复读诱饵
            cands = [it['gold']] + dec + [int(rg.integers(0, N)) for _ in range(7)]
            sp = sim_row(X, cands, it['prev'])
            sf = sim_max(X, cands, it['far'])
            b = int(np.argmax(h * sf - np.abs(sp - d)))
            hit += (b == 0)
        row.append(hit / len(sub))
    print('  h=%.1f  ' % h + '  '.join('d=%.3f:%.3f' % (dd, v)
          for dd, v in zip([0.0, 0.03, 0.066, 0.12, 0.25, 0.5, 1.0], row)))
