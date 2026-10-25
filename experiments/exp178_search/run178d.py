#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
178d: 收益到底来自"搜到的信息"还是"只是平滑"?
对照: 真外部 / 打乱的外部(保留字符频率破坏顺序) / 自己当外部
策略: 按(外部-内部)优势选位, lambda=0.20
"""
import json, math, random, sys
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp178_search')
from run178 import NG, H_of, l2, mean, load, BASE, U


def run(u, E_text, cut_frac, order=2, Xf=0.3, lam=0.2, seed=0):
    n = len(u)
    cut = int(n * cut_frac)
    Itr, T = u[:cut], u[cut:]
    vocab = set(Itr) | set(E_text) | set(T)
    MI, ME = NG(Itr, order, vocab), NG(E_text, order, vocab)
    padded = Itr + T
    p_int, p_ext, Hs = [], [], []
    for i in range(len(T)):
        pos = cut + i
        ctx = padded[max(0, pos - order):pos]
        a = T[i]
        di, de = MI.dist(ctx), ME.dist(ctx)
        p_int.append(di.get(a, 1e-12))
        p_ext.append(de.get(a, 1e-12))
        Hs.append(H_of(di))
    N = len(T)
    base = mean([l2(p) for p in p_int])
    idx = list(range(N))
    kk = max(1, int(round(Xf * N)))

    def bits(S, lm=lam):
        Ss = set(S)
        return mean([l2((1 - lm) * p_int[i] + lm * p_ext[i]) if i in Ss
                     else l2(p_int[i]) for i in idx])

    by_adv = sorted(idx, key=lambda i: math.log2(p_ext[i]) - math.log2(p_int[i]),
                    reverse=True)
    by_h = sorted(idx, key=lambda i: Hs[i], reverse=True)
    rnd = random.Random(seed)
    rr = [bits(rnd.sample(idx, kk)) for _ in range(6)]
    return {'cut': cut_frac, 'base': base,
            'by_adv': bits(by_adv[:kk]) - base,
            'by_H': bits(by_h[:kk]) - base,
            'rand': mean(rr) - base,
            'all': bits(idx) - base}


def main():
    u = load(U)
    E = load(BASE + '/external.txt')
    rnd = random.Random(7)
    Es = list(E)
    rnd.shuffle(Es)
    E_shuf = ''.join(Es)
    cuts = [0.70, 0.75, 0.80, 0.85]
    out = {}
    for name, fE in [('real', lambda c: E),
                     ('shuffled', lambda c: E_shuf),
                     ('self', lambda c: u[:int(len(u) * c)])]:
        rs = [run(u, fE(c), c) for c in cuts]
        out[name] = rs
        print('%9s  按优势选%+.4f  按H选%+.4f  随机%+.4f  全盘%+.4f'
              % (name, mean([r['by_adv'] for r in rs]),
                 mean([r['by_H'] for r in rs]),
                 mean([r['rand'] for r in rs]),
                 mean([r['all'] for r in rs])))
    with open(BASE + '/result178d.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
