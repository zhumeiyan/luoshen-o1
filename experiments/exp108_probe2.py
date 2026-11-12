import sys, numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue108 import build, sim, sim_row, sim_max

items, X = build()
N = X.shape[0]
rng = np.random.default_rng(0)
sub = [items[i] for i in rng.choice(len(items), 500, replace=False)]

print('★ 加复读诱饵：候选里混入「跟对方上一句字面最像的真人句子」')
for decoy_n in [1, 2, 3]:
    print(f'  诱饵 {decoy_n} 个 / 候选共 10 句')
    for h in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        hit, dup = 0, 0.0
        rg = np.random.default_rng(7)
        for it in sub:
            sp_all = np.asarray((X @ X[it['prev']].T).todense()).ravel()
            sp_all[it['gold']] = -1
            dec = np.argsort(-sp_all)[:decoy_n]
            cands = [it['gold']] + list(dec) + \
                    [int(rg.integers(0, N)) for _ in range(9 - decoy_n)]
            sp = sim_row(X, cands, it['prev'])
            sf = sim_max(X, cands, it['far'])
            b = int(np.argmax(h * sf + (1 - h) * sp))
            hit += (b == 0)
            dup += sim(X, cands[b], it['prev'])
        print('    h=%.1f  挑中真人 %.3f   她选的↔上一句 %.4f'
              % (h, hit / len(sub), dup / len(sub)))
print()
print('  ★ 真值：真人回应的↔上一句 %.4f（中位 %.4f）' %
      (np.mean([sim(X, it['gold'], it['prev']) for it in sub]),
       np.median([sim(X, it['gold'], it['prev']) for it in sub])))
