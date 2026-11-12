# -*- coding: utf-8 -*-
"""★109 先探：多轮 rollout 里，走岔真的会死吗？"""
import sys, numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue109 import build, partner_reply

convs, X, sents, follow, isq = build('film')
N = X.shape[0]
MAXT = 12

def rollout(mode, seed=0, nstart=60):
    rg = np.random.default_rng(seed)
    starts = rg.choice(len(convs), nstart, replace=False)
    surv, rep, conf, drift = [], [], [], []
    for ci in starts:
        c = convs[int(ci)]
        if len(c) < 3: continue
        recent = []
        p = c[0]; alive = 0; cs = []; nr = 0; dl = []
        for t in range(min(MAXT, len(c) - 2)):
            gold = c[t + 1]
            if mode == 'gold':  r = gold
            elif mode == 'rand': r = int(rg.integers(0, N))
            elif mode == 'echo': r = p
            elif mode == 'half': r = gold if (t % 2 == 0) else int(rg.integers(0, N))
            if r == gold:
                nxt = c[t + 2] if t + 2 < len(c) else gold; cs.append(1.0)
            else:
                nxt, b = partner_reply(X, follow, r, set()); cs.append(b)
            # 死法1：近3轮内说过几乎一样的话
            if any(abs(int(x) - int(r)) == 0 for x in recent[-3:]): nr += 1
            # 死法2：跟真轨迹偏了多远
            dl.append(float((X[r] @ X[gold].T)[0, 0]))
            recent.append(r)
            alive += 1
            p = nxt
        surv.append(alive / min(MAXT, len(c) - 2))
        rep.append(nr / alive); conf.append(np.mean(cs)); drift.append(np.mean(dl))
    return np.mean(surv), np.mean(rep), np.mean(conf), np.mean(drift)

print(f'{"模式":<8}{"走完比例":>10}{"3轮内重复率":>13}{"对方接续置信":>13}{"跟真轨迹重合":>13}')
for m in ['gold', 'rand', 'echo', 'half']:
    s, r, c, d = rollout(m)
    print(f'{m:<8}{s:>10.4f}{r:>13.4f}{c:>13.4f}{d:>13.4f}')
