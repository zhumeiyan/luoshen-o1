# -*- coding: utf-8 -*-
"""★109 真·话轮交替的 rollout（修正 ★109 初版里「对方把她说的话再说一遍」的错）

真对话里话轮是交替的：A 说 c0，B 说 c1，A 说 c2，B 说 c3 …
她是 B：对方（A）说 c[2t]，她该接 c[2t+1]，然后 A 说 c[2t+2]。
初版让对方说 c[t+1] —— 而那正是她刚说的话，等于对方复读她。已修。
"""
import sys, numpy as np, pickle, os
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue109 import build, split, build_follow, resp_vec, partner_reply

ROOT = '/data/workspace/luoshen-o1'


def make_batch(dom='film', maxt=5, ncand=10, ndec=2, nstart=60, seed=0):
    convs, X, sents, f_all, isq = build(dom)
    tr, te = split(convs, 0.7, seed)
    FTR = build_follow(tr)
    N = X.shape[0]
    cache = f'{ROOT}/data/exp109b_{dom}.pkl'
    if os.path.exists(cache):
        return pickle.load(open(cache, 'rb'))
    rg = np.random.default_rng(seed + 7)
    starts = [c for c in te if len(c) >= 2 * maxt + 1][:nstart]
    B = []
    for c in starts:
        rows = []
        for t in range(maxt):
            prev = c[2 * t]; gold = c[2 * t + 1]
            nxt_partner = c[2 * t + 2] if 2 * t + 2 < len(c) else None
            sp = np.asarray((X @ X[prev].T).todense()).ravel(); sp[prev] = -1
            dec = list(np.argsort(-sp)[:ndec])
            rnd = [int(rg.integers(0, N)) for _ in range(ncand - 1 - ndec)]
            C = np.array([gold] + dec + rnd)
            SP = np.asarray((X[C] @ X[prev].T).todense()).ravel()
            hist = [c[2 * j] for j in range(max(0, t - 2), t + 1)][::-1]
            SF = np.asarray((X[C] @ X[hist].T).todense()).max(axis=1)
            RV, _ = resp_vec(X, FTR, prev, C)
            rows.append(dict(prev=int(prev), gold=int(gold), C=C, SP=SP,
                             SF=SF, RV=RV,
                             nxt=int(nxt_partner) if nxt_partner is not None else -1))
        B.append(rows)
    leak = sum(1 for rows in B for r in rows
               if FTR.get(r['prev'], {}).get(r['gold'], 0) > 0)
    tot = sum(len(rows) for rows in B)
    pickle.dump(dict(B=B, X=X, sents=sents, FTR=FTR, tr=tr, te=te,
                     leak=leak, tot=tot), open(cache, 'wb'))
    return pickle.load(open(cache, 'rb'))


def rollout(batch, lam, d, a, maxt=None, mu=1.0, thr_derail=None):
    """mu>1：她若【判断自己上一轮走岔了】，这一轮把 λ 放大 mu 倍（修复）。
    thr_derail：判定走岔的阈值 —— 对方回的那句跟她刚说的相似度低于此即认为走岔。"""
    B = batch['B']; X = batch['X']; FTR = batch['FTR']
    maxt = maxt or len(B[0])
    hit = [[] for _ in range(maxt)]; conf = []; obs = []
    for rows in B:
        prev = rows[0]['prev']; derailed = False
        for t in range(maxt):
            r = rows[t]
            boost = mu if derailed else 1.0
            s = a * r['SF'] - np.abs(r['SP'] - d) + lam * boost * r['RV']
            got = int(r['C'][int(np.argmax(s))])
            hit[t].append(float(got == r['gold']))
            if got == r['gold']:
                np_ = r['nxt']
                if np_ < 0: break
                conf.append(1.0)
                obs.append((float((X[np_] @ X[got].T)[0, 0]), 0.0))
                prev = np_
            else:
                np_, b = partner_reply(X, FTR, got, set())
                conf.append(b)
                obs.append((float((X[np_] @ X[got].T)[0, 0]), 1.0))
                prev = np_
            derailed = (thr_derail is not None and obs[-1][0] < thr_derail)
    per = [np.mean(h) if h else 0.0 for h in hit]
    return dict(per=per, hit=float(np.mean([x for h in hit for x in h])),
                conf=float(np.mean(conf)), obs=obs)
