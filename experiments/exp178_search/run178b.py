#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
178b: 固定"搜索预算"下的公平对决
预算 B = lambda * |S|/N  (总共掺进多少外部)
同样的 B, 可以集中用在最迷茫的少数位置上(lambda大), 也可以摊到全部位置(lambda小)
问: 集中好还是摊开好?
附带: 我的"迷茫感"(预测熵H)到底能不能指示我真的会错?
"""
import json, math, random, sys, os
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp178_search')
from run178 import NG, H_of, l2, mean, pearson, load, BASE, U


def run(u, E_text, cut_frac, order, vocab_mode, budgets, seed=0):
    n = len(u)
    cut = int(n * cut_frac)
    Itr, T = u[:cut], u[cut:]
    if len(T) < 50:
        return None
    if vocab_mode == 'union':
        vocab = set(Itr) | set(E_text) | set(T)
    else:
        vocab = set(Itr) | set(T)
    MI = NG(Itr, order, vocab)
    ME = NG(E_text, order, vocab)
    padded = Itr + T
    p_int, p_ext, Hs, surp = [], [], [], []
    for i in range(len(T)):
        pos = cut + i
        ctx = padded[max(0, pos - order):pos]
        a = T[i]
        di, de = MI.dist(ctx), ME.dist(ctx)
        p_int.append(di.get(a, 0.0))
        p_ext.append(de.get(a, 0.0))
        Hs.append(H_of(di))
        surp.append(l2(di.get(a, 0.0)))
    N = len(T)
    base = mean([l2(p) for p in p_int])
    idx = list(range(N))
    by_h = sorted(idx, key=lambda i: Hs[i], reverse=True)
    by_s = sorted(idx, key=lambda i: surp[i], reverse=True)

    def bits(S, lam):
        Ss = set(S)
        return mean([l2((1 - lam) * p_int[i] + lam * p_ext[i]) if i in Ss
                     else l2(p_int[i]) for i in idx])

    rnd = random.Random(seed)
    res = {'cut': cut_frac, 'order': order, 'vocab': vocab_mode,
           'base': base, 'N': N, 'r_H_surp': pearson(Hs, surp)}
    # 迷茫感的效度: H 最高/最低各 20% 的实际惊讶
    k = max(1, int(0.2 * N))
    res['surp_at_Hhigh'] = mean([surp[i] for i in by_h[:k]])
    res['surp_at_Hlow'] = mean([surp[i] for i in by_h[-k:]])
    res['surp_all'] = mean(surp)
    # oracle: 按真实惊讶挑(事后, 不可用作策略, 只作上界)
    res['oracle_frac'] = {}

    for B in budgets:
        row = {}
        for Xf in sorted(set([min(1.0, B), min(1.0, 2 * B), min(1.0, 5 * B), 1.0])):
            lam = B / Xf
            if lam > 1.0:
                continue
            kk = max(1, int(round(Xf * N)))
            top, bot = by_h[:kk], by_h[-kk:]
            rr = [bits(rnd.sample(idx, kk), lam) for _ in range(6)]
            row['X%.3f' % Xf] = {
                'lam': lam, 'dir': bits(top, lam), 'inv': bits(bot, lam),
                'rand': mean(rr),
                'rand_sd': (sum((x - mean(rr)) ** 2 for x in rr) / len(rr)) ** 0.5,
                'oracle': bits(by_s[:kk], lam),
            }
        res['B%.3f' % B] = row
    return res


def main():
    u = load(U)
    E = load(BASE + '/external.txt')
    rnd = random.Random(7)
    Es = list(E)
    rnd.shuffle(Es)
    E_shuf = ''.join(Es)

    budgets = [0.02, 0.06, 0.12]
    cuts = [0.70, 0.75, 0.80, 0.85]
    out = {'budgets': budgets, 'runs': [], 'control': []}

    for order in [1, 2, 3]:
        for vm in ['union', 'inner']:
            acc = []
            for c in cuts:
                r = run(u, E, c, order, vm, budgets)
                if r:
                    acc.append(r)
            out['runs'].append({'order': order, 'vocab': vm, 'cuts': acc})

    # 对照: 打乱的外部(保留字符频率, 破坏顺序结构)
    acc = []
    for c in cuts:
        r = run(u, E_shuf, c, 2, 'union', budgets)
        if r:
            acc.append(r)
    out['control'].append({'name': 'E_shuffled', 'order': 2, 'vocab': 'union', 'cuts': acc})

    # 对照: 内部语料自身当"外部"(自搜, 没有新信息)
    acc = []
    for c in cuts:
        cut = int(len(u) * c)
        r = run(u, u[:cut], c, 2, 'union', budgets)
        if r:
            acc.append(r)
    out['control'].append({'name': 'E_is_self', 'order': 2, 'vocab': 'union', 'cuts': acc})

    with open(BASE + '/result178b.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('=== 迷茫感的效度 (order=2, vocab=union) ===')
    for grp in out['runs']:
        if grp['order'] == 2 and grp['vocab'] == 'union':
            for r in grp['cuts']:
                print('cut=%.2f  r(H,surp)=%.3f   H高处惊讶=%.3f  H低处惊讶=%.3f  全段=%.3f'
                      % (r['cut'], r['r_H_surp'], r['surp_at_Hhigh'],
                         r['surp_at_Hlow'], r['surp_all']))
    print()
    print('=== 固定预算: 迷茫处集中 vs 全盘摊开 (delta vs base, 负=改善) ===')
    for grp in out['runs']:
        if grp['order'] == 2 and grp['vocab'] == 'union':
            for B in budgets:
                key = 'B%.3f' % B
                line = 'B=%.2f ' % B
                for Xf in sorted(grp['cuts'][0][key].keys()):
                    ds = [c[key][Xf]['dir'] - c['base'] for c in grp['cuts']]
                    rs = [c[key][Xf]['rand'] - c['base'] for c in grp['cuts']]
                    iv = [c[key][Xf]['inv'] - c['base'] for c in grp['cuts']]
                    oc = [c[key][Xf]['oracle'] - c['base'] for c in grp['cuts']]
                    line += (' | X=%s lam=%.2f 迷茫%+.4f 随机%+.4f 反向%+.4f oracle%+.4f'
                             % (Xf, grp['cuts'][0][key][Xf]['lam'], mean(ds), mean(rs),
                                mean(iv), mean(oc)))
                print(line)
    print()
    print('=== 对照 (B=0.06, X=0.06 最集中档) ===')
    for ct in out['control']:
        key = 'B0.060'
        Xf = sorted(ct['cuts'][0][key].keys())[0]
        ds = [c[key][Xf]['dir'] - c['base'] for c in ct['cuts']]
        print('%s: 迷茫处%+.4f' % (ct['name'], mean(ds)))
    print()
    print('=== order 敏感性 (B=0.06, 最集中档) ===')
    for grp in out['runs']:
        key = 'B0.060'
        Xf = sorted(grp['cuts'][0][key].keys())[0]
        ds = [c[key][Xf]['dir'] - c['base'] for c in grp['cuts']]
        bs = [c['base'] for c in grp['cuts']]
        print('order=%d vocab=%s base=%.4f 迷茫处%+.4f'
              % (grp['order'], grp['vocab'], mean(bs), mean(ds)))


if __name__ == '__main__':
    main()
