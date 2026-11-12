"""★108 真多轮交流 —— 用 KdConv 真对话（1200 段、平均 24 轮）教她「接话不是复读」

★107 用的是 PTT（标题↔推文）。那里「跟上一句字面对接」有效。
但真对话里，真人回应跟上一句的字面重叠中位数只有 0.03 ——
字面最像的候选，恰恰是把对方的话说回去。那叫复读，不是接话。

语料：thu-coai/KdConv（清华）film 领域，1200 段真人多轮对话。
"""
import json, re, os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

ROOT = '/data/workspace/luoshen-o1'
KD = '/data/workspace/kdconv/film_train.json'
CACHE = f'{ROOT}/data/exp108_kdconv.npz'
OK = re.compile(r'[\u4e00-\u9fff，。！？、…0-9 ]+')
MAXH = 10          # 最多回看几轮


def txt(m):
    return m.get('message', '') if isinstance(m, dict) else ''


def build(domain='film'):
    """返回 (items, X, sents)
    items[i] = dict(prev, hist[最多MAXH句,由近到远], gold)
    """
    path = f'/data/workspace/kdconv/{domain}_train.json'
    cache = f'{ROOT}/data/exp108_{domain}.npz'
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return z['items'].tolist(), z['X'].item(), z['sents'].tolist()

    d = json.load(open(path))
    sents, items, sid = [], [], {}

    def sid_of(s):
        if s not in sid:
            sid[s] = len(sents)
            sents.append(s)
        return sid[s]

    for conv in d:
        ms = [txt(m) for m in conv['messages']]
        ms = [m for m in ms if m and m.strip()]
        for i in range(1, len(ms)):
            r = ms[i]
            if not (4 <= len(r) <= 26) or not OK.fullmatch(r):
                continue
            p = sid_of(ms[i - 1]); g = sid_of(r)
            if p == g:
                continue
            hist = [sid_of(h) for h in ms[max(0, i - 1 - MAXH):i - 1]][::-1]
            items.append(dict(prev=p, hist=hist, gold=g))

    V = TfidfVectorizer(analyzer='char', ngram_range=(1, 2))
    X = normalize(V.fit_transform(sents))
    np.savez(cache, items=np.array(items, dtype=object),
             X=np.array(X, dtype=object), sents=np.array(sents, dtype=object))
    return items, X, sents


def sim(X, i, j):
    return float((X[i] @ X[j].T)[0, 0])


def make_batch(items, X, n=None, seed=0, n_cand=10, n_decoy=2):
    """固定候选（公共随机数）。
    返回 dict(SP[c,样本], SF[c,样本,k]) —— SF 是候选与「前k轮」的最大相似度
    """
    N = X.shape[0]
    if n is None:
        n = len(items)
    idx = np.random.default_rng(seed).choice(len(items), n, replace=False)
    sub = [items[int(i)] for i in idx]
    rg = np.random.default_rng(seed + 1)
    C = []
    for it in sub:
        sp_all = np.asarray((X @ X[it['prev']].T).todense()).ravel()
        sp_all[it['gold']] = -1
        dec = list(np.argsort(-sp_all)[:n_decoy])       # 复读诱饵（含对方原话）
        rand = [int(rg.integers(0, N)) for _ in range(n_cand - 1 - n_decoy)]
        C.append([it['gold']] + dec + rand)
    C = np.array(C)                                     # [样本数, 候选数]
    SP = np.array([np.asarray((X[C[si]] @ X[it['prev']].T).todense()).ravel()
                   for si, it in enumerate(sub)])
    # SF[k]：候选与 hist 前 k 句的最大相似度
    SF = np.zeros((MAXH + 1,) + C.shape)
    for k in range(1, MAXH + 1):
        col = []
        for si, it in enumerate(sub):
            hs = it['hist'][:k]
            if not hs:
                col.append(np.zeros(C.shape[1]))
            else:
                col.append(np.asarray((X[C[si]] @ X[hs].T).todense()).max(axis=1))
        SF[k] = np.array(col)
    return dict(C=C, SP=SP, SF=SF, sub=sub)


def pick(d, k, a, B):
    """打分 = a·话题(前k轮) − |接上一句 − d|"""
    return a * B['SF'][k] - np.abs(B['SP'] - d)


def hit_rate(d, k, a, B):
    s = pick(d, k, a, B)
    return float((np.argmax(s, axis=1) == 0).mean())
