# -*- coding: utf-8 -*-
"""★109 把一段对话走完 —— 相邻对的条件相关性 + 走岔之后的修复

★108 她是「答题」：一句话孤立挑一次，说完就结束。
真交流的关键在于【你说的话会成为对方的输入】—— 选错一句，对话就走岔了。

真值（从 KdConv 真对话量出，不是我编的）：
  提问方的话里 67.6%~76.5% 是问句，答者的话里只有 27.8%~37.5%
  提问之后，真人 67.9%~80.8% 会真的回答（提供信息）   ← 条件相关性
  答者说完之后，只有 ~50% 还是答者在说               ← 角色会切换

对方模型（retrieval-based）：她说一句，对方从真语料里找「历史上跟这句最像的
话后面，真人接了什么」来回应。所以她说的话真的会改变对话的走向。
"""
import json, re, os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

ROOT = '/data/workspace/luoshen-o1'
D = '/data/workspace/kdconv'
OK = re.compile(r'[\u4e00-\u9fff，。！？、…0-9A-Za-z ]+')
Q = re.compile(r'(吗|呢|么|嘛)[？?]?$|[？?]$|(什么|为什么|怎么|怎样|哪里|哪儿|谁|几|多少|何时|哪些|哪个|如何)')


def txt(m):
    return m.get('message', '') if isinstance(m, dict) else ''


def hasattr_(m):
    return bool(m.get('attrs')) if isinstance(m, dict) else False


def build(domain='film', maxh=10):
    """返回 (convs, X, sents, follow)
    convs: list[list[句子id]]  真对话（只留合格句）
    follow[s] = {下一句id: 次数}  —— 对方模型用的真人接续统计
    """
    cache = f'{ROOT}/data/exp109_{domain}.npz'
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return (z['convs'].tolist(), z['X'].item(),
                z['sents'].tolist(), z['follow'].item(), z['isq'].tolist())

    d = json.load(open(f'{D}/{domain}_train.json'))
    sents, sid, convs, follow = [], {}, [], {}

    def sid_of(s):
        if s not in sid:
            sid[s] = len(sents); sents.append(s)
        return sid[s]

    for conv in d:
        ms = [m for m in conv['messages'] if txt(m).strip()]
        keep = [sid_of(txt(m)) for m in ms
                if 4 <= len(txt(m)) <= 26 and OK.fullmatch(txt(m))]
        if len(keep) < 4:
            continue
        convs.append(keep)
        for a, b in zip(keep[:-1], keep[1:]):
            follow.setdefault(a, {}); follow[a][b] = follow[a].get(b, 0) + 1

    V = TfidfVectorizer(analyzer='char', ngram_range=(1, 2))
    X = normalize(V.fit_transform(sents))
    isq = [bool(Q.search(s)) for s in sents]
    np.savez(cache, convs=np.array(convs, dtype=object), X=np.array(X, dtype=object),
             sents=np.array(sents, dtype=object), follow=np.array(follow, dtype=object),
             isq=np.array(isq))
    return convs, X, sents, follow, isq


def partner_reply(X, follow, said, said_set, topm=8, rng=None):
    """对方回应：找语料里跟 said 最像的若干句，按相似度加权投它们真人的接续"""
    sims = np.asarray((X @ X[said].T).todense()).ravel()
    sims[said] = -1
    top = np.argsort(-sims)[:topm]
    w = sims[top]
    w = np.clip(w, 0, None)
    if w.sum() <= 0:
        return int(np.argmax(sims)), 0.0
    vote = {}
    for s, wi in zip(top, w):
        for nx, c in follow.get(int(s), {}).items():
            vote[nx] = vote.get(nx, 0.0) + wi * c
    if not vote:
        return int(top[0]), float(sims[top[0]])
    best = max(vote.items(), key=lambda kv: kv[1])
    return int(best[0]), float(sims[top[0]])


def split(convs, frac=0.7, seed=0):
    """把对话分成「她听过的」和「没听过的」。
    follow（对方模型）只用听过的那部分建 —— 否则她等于在背答案。"""
    rg = np.random.default_rng(seed)
    idx = rg.permutation(len(convs))
    k = int(len(convs) * frac)
    return [convs[int(i)] for i in idx[:k]], [convs[int(i)] for i in idx[k:]]


def build_follow(train_convs):
    follow = {}
    for c in train_convs:
        for a, b in zip(c[:-1], c[1:]):
            follow.setdefault(a, {}); follow[a][b] = follow[a].get(b, 0) + 1
    return follow


def resp_vec(X, follow, prev, C, topm=24, soft=True):
    """responsiveness：候选 c 是不是「这句之后人真的会这么说」。
    soft=True：取「相似句子的真人接续」的加权质心，再算 c 与质心的相似度（稠密、有梯度）。
    soft=False：精确接续命中（稀疏，λ 一给大就饱和）。
    返回 (v 归一到候选内 max=1, prev 的最佳相似句置信)"""
    sims = np.asarray((X @ X[prev].T).todense()).ravel()
    sims[prev] = -1
    top = np.argsort(-sims)[:topm]
    w = np.clip(sims[top], 0, None)
    if w.sum() <= 0:
        return np.zeros(len(C)), 0.0
    if not soft:
        vote = {}
        for s, wi in zip(top, w):
            for nx, cnt in follow.get(int(s), {}).items():
                vote[nx] = vote.get(nx, 0.0) + wi * cnt
        v = np.array([vote.get(int(c), 0.0) for c in C])
        m = v.max()
        return (v / m if m > 0 else v), float(sims[top[0]])
    cen = None; tot = 0.0
    for s, wi in zip(top, w):
        for nx, cnt in follow.get(int(s), {}).items():
            vv = X[nx] * (wi * cnt)
            cen = vv if cen is None else cen + vv
            tot += wi * cnt
    if cen is None or tot <= 0:
        return np.zeros(len(C)), float(sims[top[0]])
    cen = cen / tot
    cn = float(np.sqrt(cen.multiply(cen).sum()))
    if cn <= 0:
        return np.zeros(len(C)), float(sims[top[0]])
    cen = cen / cn
    v = np.asarray((X[C] @ cen.T).todense()).ravel()
    m = v.max()
    return (v / m if m > 0 else v), float(sims[top[0]])
