# -*- coding: utf-8 -*-
"""★109 探：λ（相邻对服从度）在多轮 rollout 里有没有内部峰？"""
import sys, json, numpy as np, pickle, os
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue109 import build, split, build_follow, resp_vec, partner_reply

DOM, NCAND, NDEC, MAXT, NSTART = 'film', 10, 2, 6, 50
convs, X, sents, follow_all, isq = build(DOM)
tr, te = split(convs, 0.7, 0)
FTR = build_follow(tr)
N = X.shape[0]
print(f'train对话 {len(tr)}  test对话 {len(te)}  follow(train) {len(FTR)}')

# 固定候选（公共随机数）
rg = np.random.default_rng(7)
starts = [c for c in te if len(c) >= MAXT + 3][:NSTART]
print('starts', len(starts))

CACHE = '/data/workspace/luoshen-o1/data/exp109_batch.pkl'
if os.path.exists(CACHE):
    B = pickle.load(open(CACHE, 'rb'))
else:
    B = []
    for c in starts:
        rows = []
        for t in range(MAXT):
            prev = c[t]; gold = c[t + 1]
            sp = np.asarray((X @ X[prev].T).todense()).ravel(); sp[prev] = -1
            dec = list(np.argsort(-sp)[:NDEC])
            rnd = [int(rg.integers(0, N)) for _ in range(NCAND - 1 - NDEC)]
            C = np.array([gold] + dec + rnd)
            SP = np.asarray((X[C] @ X[prev].T).todense()).ravel()
            hist = c[max(0, t - 2):t + 1][::-1]
            SF = np.asarray((X[C] @ X[hist].T).todense()).max(axis=1) if len(hist) else np.zeros(NCAND)
            RV, conf_prev = resp_vec(X, FTR, prev, C)
            rows.append(dict(prev=prev, gold=gold, C=C, SP=SP, SF=SF, RV=RV))
        B.append(rows)
    pickle.dump(B, open(CACHE, 'wb'))
print('batch ready')


def score(r, lam, d, a, boost=1.0):
    return a * r['SF'] - np.abs(r['SP'] - d) + lam * boost * r['RV']


def rollout(lam, d, a, mu=1.0, turns=MAXT):
    """mu：走岔之后把 λ 放大多少倍（修复倾向）"""
    dr, cf, hit = [], [], []
    for rows in B:
        prev = rows[0]['prev']
        for t in range(turns):
            r = rows[t]
            boost = mu if (t > 0 and prev != rows[t - 1].get('nxt_gold_sentinel')) else 1.0
            s = score(r, lam, d, a, boost)
            pick = int(np.argmax(s))
            got = int(r['C'][pick])
            dr.append(float((X[got] @ X[r['gold']].T)[0, 0]))
            hit.append(float(got == r['gold']))
            # 对方回应
            if got == r['gold']:
                nxt = rows[t + 1]['prev'] if t + 1 < turns else got
                cf.append(1.0)
            else:
                nxt, b = partner_reply(X, FTR, got, set()); cf.append(b)
            prev = nxt
    return float(np.mean(hit)), float(np.mean(dr)), float(np.mean(cf))


print(f'\n{"lam":>6}{"命中":>9}{"跟真轨迹重合":>14}{"对方接续置信":>13}')
for lam in [0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]:
    h, dr, cf = rollout(lam, 0.18, 0.25)
    print(f'{lam:>6}{h:>9.4f}{dr:>14.4f}{cf:>13.4f}')
