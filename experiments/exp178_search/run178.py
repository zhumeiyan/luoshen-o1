#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
178: 迷茫时才搜 —— 外部信源该加在哪一拍
目标: 预测用户侧下一句(u_side.txt)
内部: 用户历史前段(我已看见你的部分)
外部: 真抓取的中文论述(external.txt)
干预: 把外部模型的概率混进内部模型, 区别在于"混在哪些位置"
  有方向(只在预测熵高处) / 反向(在熵低处) / 随机 / 全盘
"""
import json, math, random, os, hashlib
from collections import Counter, defaultdict

BASE = '/data/workspace/luoshen-o1/experiments/exp178_search'
U = '/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt'
ORDER = 2          # 176号: 眼深 2
MU = 1.0
ALPHA = 0.1


def load(p):
    with open(p, encoding='utf-8') as f:
        return f.read().strip()


class NG:
    """字符 n-gram, 递归插值 backoff"""

    def __init__(self, text, order, vocab, mu=MU, alpha=ALPHA):
        self.order = order
        self.vocab = sorted(vocab)
        self.mu, self.alpha = mu, alpha
        self.cnt = [defaultdict(Counter) for _ in range(order + 1)]
        self.tot = [dict() for _ in range(order + 1)]
        for i, ch in enumerate(text):
            for j in range(1, order + 1):
                if i - j >= 0:
                    self.cnt[j][text[i - j:i]][ch] += 1
        for j in range(1, order + 1):
            for ctx, c in self.cnt[j].items():
                self.tot[j][ctx] = sum(c.values())
        self.uni = Counter(ch for ch in text if ch in vocab)
        self.tot0 = sum(self.uni.values())
        self._cache = {}

    def _uni(self):
        V = len(self.vocab)
        denom = self.tot0 + self.alpha * V
        return {ch: (self.uni.get(ch, 0) + self.alpha) / denom for ch in self.vocab}

    def dist(self, ctx):
        j = min(len(ctx), self.order)
        return self._d(ctx[-j:] if j > 0 else '', j)

    def _d(self, ctx, j):
        key = (ctx, j)
        if key in self._cache:
            return self._cache[key]
        if j == 0:
            r = self._uni()
        else:
            c = self.cnt[j].get(ctx)
            t = self.tot[j].get(ctx, 0)
            if t == 0:
                r = self._d(ctx[1:] if j > 1 else '', j - 1)
            else:
                lam = t / (t + self.mu)
                back = self._d(ctx[1:] if j > 1 else '', j - 1)
                r = {ch: lam * (c.get(ch, 0) / t) + (1 - lam) * back[ch]
                     for ch in self.vocab}
        self._cache[key] = r
        return r


def H_of(d):
    return -sum(p * math.log2(p) for p in d.values() if p > 0)


def l2(p):
    return -math.log2(max(p, 1e-12))


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def pearson(a, b):
    n = len(a)
    ma, mb = mean(a), mean(b)
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((x - mb) ** 2 for x in b))
    return num / (da * db) if da > 0 and db > 0 else float('nan')


def run_one(u, E_text, cut_frac, lam_list, X_list, seed=0):
    n = len(u)
    cut = int(n * cut_frac)
    Itr, T = u[:cut], u[cut:]
    if len(T) < 50:
        return None

    vocab = set(Itr) | set(E_text) | set(T)
    MI = NG(Itr, ORDER, vocab)
    MU1 = NG(Itr, 1, vocab)          # 总结版(unigram)
    ME = NG(E_text, ORDER, vocab)

    padded = Itr + T
    p_int, p_ext, p_uni, Hs, surp = [], [], [], [], []
    for i in range(len(T)):
        pos = cut + i
        ctx = padded[max(0, pos - ORDER):pos]
        actual = T[i]
        di = MI.dist(ctx)
        de = ME.dist(ctx)
        du = MU1.dist(ctx)
        p_int.append(di.get(actual, 0.0))
        p_ext.append(de.get(actual, 0.0))
        p_uni.append(du.get(actual, 0.0))
        Hs.append(H_of(di))
        surp.append(l2(di.get(actual, 0.0)))

    base = mean([l2(p) for p in p_int])
    base_uni = mean([l2(p) for p in p_uni])
    base_ext = mean([l2(p) for p in p_ext])

    idx = list(range(len(T)))
    by_h = sorted(idx, key=lambda i: Hs[i], reverse=True)

    def bits_for(S, lam):
        out = []
        Sset = set(S)
        for i in idx:
            if i in Sset:
                out.append(l2((1 - lam) * p_int[i] + lam * p_ext[i]))
            else:
                out.append(l2(p_int[i]))
        return mean(out)

    res = {'cut': cut_frac, 'n_test': len(T), 'base': base,
           'base_unigram': base_uni, 'base_external_only': base_ext,
           'H_vs_surprise_r': pearson(Hs, surp),
           'mean_H': mean(Hs)}

    rnd = random.Random(seed)
    for lam in lam_list:
        for X in X_list:
            k = max(1, int(round(X * len(T))))
            top = by_h[:k]
            bot = by_h[-k:]
            tag = 'lam%.2f_X%.2f' % (lam, X)
            res['dir_' + tag] = bits_for(top, lam)      # 迷茫处搜
            res['inv_' + tag] = bits_for(bot, lam)      # 不迷茫处搜
            res['all_' + tag] = bits_for(idx, lam) if X >= 1.0 else None
            rr = []
            for s in range(5):
                samp = rnd.sample(idx, k)
                rr.append(bits_for(samp, lam))
            res['rand_' + tag] = mean(rr)
    # 全盘单独扫 lam
    for lam in lam_list:
        res['all_lam%.2f' % lam] = bits_for(idx, lam)
    return res


def main():
    u = load(U)
    E = load(BASE + '/external.txt')
    rnd0 = random.Random(7)
    E_shuf = list(E)
    rnd0.shuffle(E_shuf)
    E_shuf = ''.join(E_shuf)

    lam_list = [0.1, 0.2, 0.3, 0.5]
    X_list = [0.05, 0.1, 0.2, 0.3, 0.5]
    cuts = [0.70, 0.75, 0.80, 0.85]

    out = {'order': ORDER, 'mu': MU, 'alpha': ALPHA,
           'len_u': len(u), 'len_E': len(E),
           'sha_u': hashlib.sha256(u.encode()).hexdigest()[:12],
           'sha_E': hashlib.sha256(E.encode()).hexdigest()[:12],
           'cuts': [], 'Efrac': [], 'shuffle_control': []}

    for c in cuts:
        r = run_one(u, E, c, lam_list, X_list)
        if r:
            out['cuts'].append(r)

    # 搜多少才够: E 比例扫描 (固定 cut=0.8, lam=0.3, X=0.2)
    for frac in [0.1, 0.25, 0.5, 1.0]:
        Es = E[:int(len(E) * frac)]
        if len(Es) < 100:
            continue
        r = run_one(u, Es, 0.80, [0.3], [0.2])
        if r:
            r['Efrac'] = frac
            r['E_len'] = len(Es)
            out['Efrac'].append(r)

    # 对照: 打乱的外部语料(保留字符频率, 破坏顺序)
    r = run_one(u, E_shuf, 0.80, [0.3], [0.2])
    if r:
        out['shuffle_control'].append(r)

    # 等长对照: E 截断到与内部训练集等长
    cut80 = int(len(u) * 0.80)
    Eeq = E[:cut80]
    r = run_one(u, Eeq, 0.80, [0.3], [0.2])
    if r:
        r['E_len'] = len(Eeq)
        out['shuffle_control'].append({'note': 'E_equal_len', **r})

    with open(BASE + '/result178.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('len_u=%d len_E=%d' % (len(u), len(E)))
    for r in out['cuts']:
        print('cut=%.2f n=%d base=%.4f uni=%.4f ext_only=%.4f r(H,surp)=%.3f'
              % (r['cut'], r['n_test'], r['base'], r['base_unigram'],
                 r['base_external_only'], r['H_vs_surprise_r']))
    print('--- lam=0.30 (delta vs base, 负=改善) ---')
    for X in X_list:
        tag = 'lam0.30_X%.2f' % X
        ds = [c['dir_' + tag] - c['base'] for c in out['cuts']]
        iv = [c['inv_' + tag] - c['base'] for c in out['cuts']]
        rd = [c['rand_' + tag] - c['base'] for c in out['cuts']]
        print('X=%.2f  迷茫处%+.4f  不迷茫处%+.4f  随机%+.4f'
              % (X, mean(ds), mean(iv), mean(rd)))
    for lam in lam_list:
        al = [c['all_lam%.2f' % lam] - c['base'] for c in out['cuts']]
        print('全盘 lam=%.2f  %+.4f' % (lam, mean(al)))
    print('--- 搜多少 ---')
    for r in out['Efrac']:
        tag = 'lam0.30_X0.20'
        print('Efrac=%.2f E_len=%d base=%.4f 迷茫处%+.4f'
              % (r['Efrac'], r['E_len'], r['base'], r['dir_' + tag] - r['base']))
    for r in out['shuffle_control']:
        tag = 'lam0.30_X0.20'
        nt = r.get('note', 'E_shuffled')
        print('%s: base=%.4f 迷茫处%+.4f' % (nt, r['base'], r['dir_' + tag] - r['base']))


if __name__ == '__main__':
    main()
