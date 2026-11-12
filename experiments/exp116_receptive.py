#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp116 —— 理解先于产出（receptive >> productive）

════ 为什么这一课 ════
  ★112 我列过领域顶尖的人会做而我没做的：
    "先测理解，不许先测产出。12月龄婴儿理解约50词，产出只有1~3词。"
  我 115 课全在测产出，一个理解测验都没有。这一课补上。

  儿童语料（CHILDES/CDS）确实拿不到 —— 试过 5 条路全被拦。
  但"理解先于产出"这条真值不需要 CDS，它是跨语言的普遍规律。

════ 真值（文献，REAL）════
  12月龄  理解 ~50 词，产出 1~3 词     比 ~17~50
  16月龄  理解 ~170 词，产出 ~40 词     比 ~4
  18月龄  理解 ~200+，产出 ~50~100     比 ~2~4
  ★ 关键形状：理解集【严格包含】产出集，且差距随年龄收敛

════ 与"做题"的区别 ════
  理解 = 给定上下文，从候选里【认出】正确的词（有提示）
  产出 = 给定上下文，自己【生成】那个词（无提示）
  这两件事在真婴儿身上差 10 倍以上。如果她身上差不到，
  说明我造的"产出"根本不是产出。

════ 外部证据 ════
  分词金标 pkuseg（北大，外部工具）
  语料     KdConv 真实中文对话（12万真实汉字，非我生成）
"""

from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pkuseg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'exp116_receptive.json')

# ── 文献真值（MacArthur-Bates CDI 常模，REAL）──
CDI_NORMS = {
    '12mo': {'receptive': 50, 'productive': 3, 'ratio': 16.7},
    '16mo': {'receptive': 170, 'productive': 40, 'ratio': 4.25},
    '18mo': {'receptive': 200, 'productive': 75, 'ratio': 2.67},
}

_SEG = pkuseg.pkuseg()


def load_corpus(n_chars=120000):
    txt = []
    for name in ('film_train.json', 'music_train.json', 'travel_train.json'):
        fp = os.path.join(os.path.dirname(ROOT), 'kdconv', name)
        if not os.path.exists(fp):
            continue
        try:
            d = json.load(open(fp, encoding='utf-8'))
        except Exception:
            continue
        for item in d:
            for m in item.get('messages', []):
                if isinstance(m, dict):
                    v = m.get('message')
                    if isinstance(v, str):
                        txt.append(v)
    s = re.sub(r'[^\u4e00-\u9fff]', '', ''.join(txt))
    return s[:n_chars]


def main():
    print('[1/6] 真实语料 + pkuseg 外部分词...')
    corpus = load_corpus()
    if len(corpus) < 20000:
        print('  ✗ 语料不足，终止（不编造）')
        return
    sents = [corpus[i:i + 20] for i in range(0, len(corpus) - 20, 20)][:5000]
    tokenized = [_SEG.cut(s) for s in sents]
    from collections import Counter
    freq = Counter()
    for w in tokenized:
        freq.update(x for x in w if len(x) >= 1)
    vocab = [w for w, c in freq.most_common(600)]
    print(f'      语料 {len(corpus)} 汉字，词表 {len(vocab)}')

    print('[2/6] 建上下文分布（她能听到的）...')
    # 词的左/右邻词分布 = 她从语流中能统计到的东西
    left_ctx, right_ctx = {}, {}
    for toks in tokenized:
        for i, w in enumerate(toks):
            if w not in freq:
                continue
            l = toks[i - 1] if i > 0 else '<S>'
            r = toks[i + 1] if i + 1 < len(toks) else '</S>'
            left_ctx.setdefault(w, Counter())[l] += 1
            right_ctx.setdefault(w, Counter())[r] += 1

    # ── 理解测试：给定上下文，从候选里认出正确的词 ──
    print('[3/6] 理解测试（有候选，认出来）...')
    rng = np.random.default_rng(0)
    K = 10          # 10 选 1
    n_trial = 3000
    correct = 0
    receptive_ok = set()
    for _ in range(n_trial):
        # 选一个有足够上下文的词
        target = vocab[rng.integers(0, min(len(vocab), 300))]
        lc = left_ctx.get(target)
        if not lc or sum(lc.values()) < 2:
            continue
        # 取它最常见的一个左邻作为线索
        cue = lc.most_common(1)[0][0]
        # 候选：target + K-1 个干扰
        distract = [w for w in vocab if w != target]
        cands = [target] + list(rng.choice(distract, K - 1, replace=False))
        # 她的判断：哪个候选在 cue 后面出现得最多（这就是分布语义/理解）
        scores = []
        for c in cands:
            # P(c | cue) 用左邻统计估计
            rc = left_ctx.get(c, Counter())
            tot = sum(rc.values())
            scores.append(rc.get(cue, 0) / tot if tot > 0 else 0.0)
        if int(np.argmax(scores)) == 0:
            correct += 1
            receptive_ok.add(target)
    rec_acc = correct / max(n_trial, 1)
    print(f'      理解准确率 {rec_acc:.4f}  (随机基线 {1/K:.4f})')

    # ── 产出测试：给定同样的上下文，自己生成那个词 ──
    print('[4/6] 产出测试（无候选，自己说出来）...')
    prod_ok = set()
    n_prod = 0
    prod_hit = 0
    for _ in range(n_trial):
        target = vocab[rng.integers(0, min(len(vocab), 300))]
        lc = left_ctx.get(target)
        if not lc or sum(lc.values()) < 2:
            continue
        cue = lc.most_common(1)[0][0]
        n_prod += 1
        # 产出：她只能从自己学过的分布里【采样】一个词
        # 用整个词表按 P(w | cue) 采样，看是否命中 target
        ws, ps = [], []
        for w in vocab[:300]:
            rc = left_ctx.get(w, Counter())
            tot = sum(rc.values())
            ws.append(w)
            ps.append(rc.get(cue, 0) / tot if tot > 0 else 0.0)
        ps = np.array(ps)
        if ps.sum() <= 0:
            continue
        ps = ps / ps.sum()
        gen = ws[int(rng.choice(len(ws), p=ps))]
        if gen == target:
            prod_hit += 1
            prod_ok.add(target)
    prod_acc = prod_hit / max(n_prod, 1)
    print(f'      产出准确率 {prod_acc:.4f}')

    # ── 关键检验：理解集 ⊋ 产出集 ──
    print('[5/6] 检验 理解集 ⊋ 产出集（文献硬要求）...')
    only_rec = len(receptive_ok - prod_ok)
    only_prod = len(prod_ok - receptive_ok)
    both = len(receptive_ok & prod_ok)
    ratio = len(receptive_ok) / max(len(prod_ok), 1)
    print(f'      理解集 {len(receptive_ok)}   产出集 {len(prod_ok)}')
    print(f'      只在理解里 {only_rec}   只在产出里 {only_prod}   交集 {both}')
    print(f'      理解/产出 = {ratio:.2f}')
    containment = only_prod / max(len(prod_ok), 1)
    print(f'      ★ 违反包含关系的比例 {containment:.4f}  (文献要求 ≈ 0)')

    print('[6/6] 对照文献常模...')
    for age, v in CDI_NORMS.items():
        print(f'      {age}: 理解 {v["receptive"]}  产出 {v["productive"]}  比 {v["ratio"]}')

    res = {
        'vocab_size': len(vocab),
        'receptive_accuracy': float(rec_acc),
        'productive_accuracy': float(prod_acc),
        'random_baseline': 1.0 / K,
        'receptive_set': len(receptive_ok),
        'productive_set': len(prod_ok),
        'only_receptive': only_rec,
        'only_productive': only_prod,
        'intersection': both,
        'ratio': float(ratio),
        'containment_violation': float(containment),
        'cdi_norms': CDI_NORMS,
        'corpus_chars': len(corpus),
        'note': '语料为成人对话(KdConv)，非儿童导向言语；'
                '理解/产出的【形状】可检验，绝对值不可与CDI常模直接比较',
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f'\n已存 {OUT}')


if __name__ == '__main__':
    main()
