#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp115 —— 外部裁判：用 pkuseg（北大分词器，不是我写的）当金标

════ 为什么这一课重要 ════
  ★112/★113 我连续三次差点报假成绩，根因都一样：
  语料我造、金标我造、分数我算。我是老师、考官、阅卷人。
  这一课金标来自 pkuseg —— 一个外部的、学界公认的中文分词器。
  我第一次不能用"我的尺子"给她发成绩单。

════ 外部证据链 ════
  工具   pkuseg（北大，ACL 收录）  ← 已安装并验证
  语料   KdConv 真实中文对话（106 万真实汉字）  ← 不是我生成的
  指标   AUC（不被"猜正比例"顶上去）+ always-positive 基线

════ 预注册（跑前写定，跑后不改）════
  P1  always-positive 基线必须报告（50/50 平衡下准确率 ≈0.667，AUC=0.5）
  P2  只报 AUC，不报 F1/accuracy（F1 会被猜正比例顶到 0.99）
  P3  负样本用"真词内部"不构造（否则 AUC 虚高 +0.29，★113 教训）
  P4  报告人类天花板（中文分词人际一致率 ~90~95%）
"""

from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'exp115_external.json')

# ── 外部工具：pkuseg（外部，不是我写的）──
import pkuseg
_SEG = pkuseg.pkuseg()


def load_real_corpus(n_chars=200000):
    """真实中文对话语料（KdConv），不是我生成的"""
    txt = []
    for name in ('film_train.json', 'music_train.json', 'travel_train.json'):
        fp = os.path.join(os.path.dirname(ROOT), 'kdconv', name)
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, encoding='utf-8') as f:
                obj = json.load(f)
        except Exception:
            continue
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ('content','message') and isinstance(v, str):
                        txt.append(v)
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(obj)
    s = ''.join(txt)
    s = re.sub(r'[^\u4e00-\u9fff]', '', s)
    return s[:n_chars]


def gold_boundaries(sentences):
    """pkuseg 分词 → 边界真值（外部金标）"""
    gold, chars = [], []
    for s in sentences:
        words = _SEG.cut(s)
        cs = list(s)
        # 每个词内部最后一个字之后是边界
        lab = [0] * (len(cs) - 1)
        i = 0
        for w in words:
            i += len(w)
            if i - 1 < len(lab):
                lab[i - 1] = 1
        if len(cs) > 1:
            gold.extend(lab)
            chars.extend(cs)
    return np.array(gold), chars


def stat_features_global(text, n_take=None):
    """★全语料统计（不是局部窗口）——局部40字窗口太稀疏，PMI估不出来"""
    from collections import Counter
    big=Counter(); uni=Counter()
    for i in range(len(text)-1):
        big[text[i:i+2]]+=1; uni[text[i]]+=1
    tot_b=sum(big.values()); tot_u=sum(uni.values())
    def pmi(a,b):
        pb=big.get(a+b,0)/tot_b; pa=uni.get(a,0)/tot_u; pc=uni.get(b,0)/tot_u
        return np.log((pb+1e-12)/(pa*pc+1e-12))
    return pmi, big, uni

def stat_features(chars, k=3):
    """
    统计学习特征（她能观测的）：
      1) 左分支熵 / 右分支熵（语境多样性）
      2) 内部凝聚度（互信息）
    这些是 Saffran/统计学习范式能算的量。
    """
    n = len(chars)
    if n < k * 2 + 2:
        return None
    # 计数
    from collections import defaultdict
    uniq = {}
    for kk in (1, 2, 3):
        d = defaultdict(int)
        for i in range(n - kk + 1):
            d[''.join(chars[i:i + kk])] += 1
        uniq[kk] = d

    def entropy(d):
        tot = sum(d.values())
        if tot == 0:
            return 0.0
        return -sum((v / tot) * np.log(v / tot + 1e-12) for v in d.values())

    left_ent, right_ent, mi = [], [], []
    for i in range(n - 1):
        c = chars[i]
        # 左分支熵：前面一个字 + 当前字 的多样性
        ld = defaultdict(int)
        for j in range(max(0, i - 40), i):
            ld[chars[j]] += 1
        rd = defaultdict(int)
        for j in range(i + 1, min(n, i + 41)):
            rd[chars[j]] += 1
        left_ent.append(entropy(ld))
        right_ent.append(entropy(rd))
        # 互信息：bigram 凝聚度
        bg = ''.join(chars[i:i + 2])
        p_bg = uniq[2].get(bg, 0) / max(n - 1, 1)
        p_a = uniq[1].get(chars[i], 0) / max(n, 1)
        p_b = uniq[1].get(chars[i + 1], 0) / max(n, 1)
        mi.append(np.log((p_bg + 1e-12) / (p_a * p_b + 1e-12)))
    return np.array(left_ent), np.array(right_ent), np.array(mi)


def auc(y, s):
    """AUC（不被猜正比例顶上去）"""
    y = np.asarray(y, dtype=int)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    order = np.argsort(s)
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    # 处理并列
    srt = np.sort(s)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and srt[j + 1] == srt[i]:
            j += 1
        if j > i:
            avg = (i + j + 2) / 2.0
            ranks[(s >= srt[i]) & (s <= srt[j])] = avg
        i = j + 1
    return (ranks[y == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    print('[1/5] 载入真实语料（KdConv）...')
    corpus = load_real_corpus(120000)
    print(f'      真实汉字 {len(corpus)}')
    if len(corpus) < 5000:
        print('      ✗ 语料不足，终止（不编造数据）')
        return

    # 切句（按长度，不按标点——标点已被剥离）
    sents = [corpus[i:i + 18] for i in range(0, len(corpus) - 18, 18)]
    sents = sents[:4000]
    print(f'      句子 {len(sents)}')

    print('[2/5] pkuseg 生成外部金标...')
    gold, chars = gold_boundaries(sents)
    print(f'      边界位 {len(gold)}  正例率 {gold.mean():.4f}')

    print('[3/5] 统计学习特征（全语料 bigram，双向检验）...')
    pmi_fn, bigc, uniq1 = stat_features_global(corpus)
    # ★ 必须【句内】计算：gold 每句 len(cs)-1 个边界，chars 每句 len(cs) 个字符。
    #   直接对拼接后的 chars 算会跨句错位 → 特征与真值对不上 → 塌回 0.50。
    mi, fr = [], []
    for sen in sents:
        cs = list(sen)
        for j in range(len(cs) - 1):
            mi.append(pmi_fn(cs[j], cs[j+1]))
            fr.append(bigc.get(''.join(cs[j:j+2]), 0))
    mi = np.array(mi); fr = np.array(fr, dtype=float)
    le = np.zeros_like(mi); re_ = np.zeros_like(mi)
    n = min(len(gold), len(mi), len(fr))
    gold, mi, fr, le, re_ = gold[:n], mi[:n], fr[:n], le[:n], re_[:n]

    print('[4/5] 基线（预注册 P1/P2）...')
    # always-positive 基线
    ap_acc = gold.mean()
    # 随机
    rng = np.random.default_rng(0)
    rnd = rng.random(n)
    res = {
        'n_boundaries': int(n),
        'positive_rate': float(gold.mean()),
        'always_positive_accuracy': float(ap_acc),
        'random_auc': float(auc(gold, rnd)),
    }
    print(f'      always-positive 准确率 {ap_acc:.4f}（预注册 P1：必须报告）')
    print(f'      随机 AUC {res["random_auc"]:.4f}')

    print('[5/5] 她的特征 → AUC（外部金标）...')
    # ★双向：PMI 正向 vs 负向（★113 教训：方向必须两个都跑）
    res['auc_pmi_positive'] = float(auc(gold, mi))
    res['auc_pmi_negative'] = float(auc(gold, -mi))
    res['auc_bigram_freq'] = float(auc(gold, fr))
    for k in ('auc_pmi_positive', 'auc_pmi_negative', 'auc_bigram_freq'):
        print(f'      {k:26s} {res[k]:.4f}')
    # 外部天花板：jieba vs pkuseg 一致率
    import jieba
    inter=0; unio=0
    for sen in sents[:300]:
        a=set(); b=set(); i=0
        for w in jieba.cut(sen):
            i+=len(w); a.add(i-1)
        i=0
        for w in _SEG.cut(sen):
            i+=len(w); b.add(i-1)
        inter+=len(a&b); unio+=len(a|b)
    res['external_tool_agreement'] = float(inter/max(unio,1))
    _k = 'external_tool_agreement'
    print('      %-26s %.4f  <-- ceiling' % (_k, res[_k]))

    # 预注册 P4：人类天花板
    res['human_ceiling_note'] = '中文分词人际一致率约 90~95%（SIGHAN bakeoff），超过即疑金标泄露'

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f'\n已存 {OUT}')


if __name__ == '__main__':
    main()
