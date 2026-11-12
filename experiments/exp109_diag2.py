# -*- coding: utf-8 -*-
"""★109 诊断：① λ 的好处是不是随轮次放大（复利）② 走岔能不能被她观测到"""
import sys, pickle, numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.dialogue109 import build, partner_reply
convs, X, sents, f, isq = build('film')
B = pickle.load(open('/data/workspace/luoshen-o1/data/exp109_batch.pkl', 'rb'))
N = X.shape[0]; MAXT = 6

def histsim(prev, C):  # 复用：SF 已存
    pass

def run(lam, d=0.18, a=0.25):
    per = [[] for _ in range(MAXT)]; obs = []
    for rows in B:
        prev = rows[0]['prev']
        for t in range(MAXT):
            r = rows[t]
            s = a * r['SF'] - np.abs(r['SP'] - d) + lam * r['RV']
            got = int(r['C'][int(np.argmax(s))])
            per[t].append(float(got == r['gold']))
            if got == r['gold']:
                nxt = rows[t + 1]['prev'] if t + 1 < MAXT else got
            else:
                nxt, b = partner_reply(X, f, got, set())
            # 观测：对方回的这句，跟她刚说的像不像
            obs.append((float((X[nxt] @ X[got].T)[0, 0]), float(got != r['gold'])))
            prev = nxt
    return [np.mean(p) for p in per], obs

print('== ① 逐轮命中：λ 的好处是不是随轮次放大 ==')
h0, obs0 = run(0.0)
h1, obs1 = run(0.25)
print(f'{"轮":>3}{"λ=0":>9}{"λ=0.25":>9}{"差":>9}')
for t in range(MAXT):
    print(f'{t:>3}{h0[t]:>9.4f}{h1[t]:>9.4f}{h1[t]-h0[t]:>+9.4f}')
print(f'{"总":>3}{np.mean(h0):>9.4f}{np.mean(h1):>9.4f}{np.mean(h1)-np.mean(h0):>+9.4f}')

print('\n== ② 走岔能不能被她观测到（AUC）==')
o = np.array(obs1)
sc, y = o[:, 0], o[:, 1].astype(int)
pos, neg = sc[y == 1], sc[y == 0]
print(f'  真走岔 n={len(pos)} 均值 {pos.mean():.4f}')
print(f'  没走岔 n={len(neg)} 均值 {neg.mean():.4f}')
r = np.argsort(np.argsort(sc))
auc = (r[y == 1].sum() - len(pos) * (len(pos) - 1) / 2) / (len(pos) * len(neg))
print(f'  AUC = {auc:.4f}   (>0.5 才可观测，越高越能自己发现走岔)')
