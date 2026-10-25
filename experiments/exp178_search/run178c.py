#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
178c: 外部信源在我迷茫处是否相对更强? 以及最优信任度 lambda
1) 按预测熵 H 分 10 档, 看每档上 外部/内部 的相对优势
2) 在迷茫处扫 lambda, 找最优信任度
3) 策略对比: 按H选 vs 按(外部-内部)优势选 vs 随机
"""
import json, math, random, sys
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp178_search')
from run178 import NG, H_of, l2, mean, pearson, load, BASE, U


def run(u, E_text, cut_frac, order=2, seed=0):
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
    rnd = random.Random(seed)

    # 1) H 分档, 看相对优势
    order_idx = sorted(idx, key=lambda i: Hs[i])
    nb = 10
    bands = []
    for b in range(nb):
        lo = int(b * N / nb)
        hi = int((b + 1) * N / nb)
        grp = order_idx[lo:hi]
        adv = mean([math.log2(p_ext[i]) - math.log2(p_int[i]) for i in grp])
        bands.append({'band': b, 'mean_H': mean([Hs[i] for i in grp]),
                      'mean_surp': mean([l2(p_int[i]) for i in grp]),
                      'adv_ext_over_int': adv, 'n': len(grp)})

    def bits(S, lam):
        Ss = set(S)
        return mean([l2((1 - lam) * p_int[i] + lam * p_ext[i]) if i in Ss
                     else l2(p_int[i]) for i in idx])

    by_h = sorted(idx, key=lambda i: Hs[i], reverse=True)
    by_adv = sorted(idx, key=lambda i: math.log2(p_ext[i]) - math.log2(p_int[i]),
                    reverse=True)

    res = {'cut': cut_frac, 'base': base, 'N': N, 'bands': bands,
           'r_H_surp': pearson(Hs, [l2(p) for p in p_int])}

    # 2) 迷茫处扫 lambda
    res['lam_sweep'] = {}
    for Xf in [0.1, 0.2, 0.3, 0.5]:
        kk = max(1, int(round(Xf * N)))
        top = by_h[:kk]
        row = {}
        for lam in [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
            row['%.2f' % lam] = bits(top, lam) - base
        res['lam_sweep']['X%.2f' % Xf] = row

    # 3) 三种选位策略, 固定 lam=0.2
    res['strategy'] = {}
    for Xf in [0.1, 0.2, 0.3, 0.5]:
        kk = max(1, int(round(Xf * N)))
        rr = [bits(rnd.sample(idx, kk), 0.2) for _ in range(6)]
        res['strategy']['X%.2f' % Xf] = {
            'by_H': bits(by_h[:kk], 0.2) - base,
            'by_adv': bits(by_adv[:kk], 0.2) - base,
            'rand': mean(rr) - base,
            'rand_sd': (sum((x - mean(rr)) ** 2 for x in rr) / len(rr)) ** 0.5,
        }
    return res


def main():
    u = load(U)
    E = load(BASE + '/external.txt')
    cuts = [0.70, 0.75, 0.80, 0.85]
    out = []
    for c in cuts:
        out.append(run(u, E, c))
    with open(BASE + '/result178c.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('=== 相对优势 vs 迷茫程度 (按 H 分 10 档, 跨 cut 平均) ===')
    print('档位  平均H   平均惊讶   外部-内部(bits)')
    for b in range(10):
        mh = mean([r['bands'][b]['mean_H'] for r in out])
        ms = mean([r['bands'][b]['mean_surp'] for r in out])
        ad = mean([r['bands'][b]['adv_ext_over_int'] for r in out])
        print(' %2d   %6.3f   %6.3f    %+7.4f' % (b, mh, ms, ad))
    print()
    print('=== 迷茫处该信外部多少 (delta vs base) ===')
    for Xf in ['X0.10', 'X0.20', 'X0.30', 'X0.50']:
        row = 'X=%s ' % Xf
        for lam in ['0.05', '0.10', '0.20', '0.30', '0.50', '0.70', '1.00']:
            v = mean([r['lam_sweep'][Xf][lam] for r in out])
            row += ' | λ=%s %+.4f' % (lam, v)
        print(row)
    print()
    print('=== 选位策略 (λ=0.20) ===')
    for Xf in ['X0.10', 'X0.20', 'X0.30', 'X0.50']:
        bh = mean([r['strategy'][Xf]['by_H'] for r in out])
        ba = mean([r['strategy'][Xf]['by_adv'] for r in out])
        rd = mean([r['strategy'][Xf]['rand'] for r in out])
        sd = mean([r['strategy'][Xf]['rand_sd'] for r in out])
        print('X=%s  按H选%+.4f  按优势选%+.4f  随机%+.4f (随机sd %.4f)'
              % (Xf, bh, ba, rd, sd))


if __name__ == '__main__':
    main()
