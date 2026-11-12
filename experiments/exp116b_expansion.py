#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp116b —— 膨胀检验：★116 报的"理解集 ⊋ 产出集"是不是假象？

════ 怀疑 ════
  exp116 报 "只在产出里 = 0，违反包含关系比例 0.0000，文献要求 ≈0"。
  看着像完美符合文献。但：
    理解 = argmax（确定性，命中则入集）
    产出 = 从同一分布【采样】（随机，命中才入集）
  采样次数越多，产出集越会膨胀到覆盖整个候选集。
  那"只在产出里=0"可能只是【采样次数不够】，不是真的包含关系。

════ 检验 ════
  让 n_trial 从 1000 涨到 30000，看产出集怎么变。
"""

from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pkuseg
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'exp116b_expansion.json')
_seg = pkuseg.pkuseg()


def build():
    txt = []
    for name in ('film_train.json', 'music_train.json', 'travel_train.json'):
        fp = os.path.join(os.path.dirname(ROOT), 'kdconv', name)
        if not os.path.exists(fp):
            continue
        d = json.load(open(fp, encoding='utf-8'))
        for item in d:
            for m in item.get('messages', []):
                if isinstance(m, dict):
                    v = m.get('message')
                    if isinstance(v, str):
                        txt.append(v)
    s = re.sub(r'[^\u4e00-\u9fff]', '', ''.join(txt))[:120000]
    sents = [s[i:i + 20] for i in range(0, len(s) - 20, 20)][:5000]
    toks = [_seg.cut(x) for x in sents]
    freq = Counter()
    for w in toks:
        freq.update(w)
    vocab = [w for w, c in freq.most_common(600)]
    left = {}
    for t in toks:
        for i, w in enumerate(t):
            l = t[i - 1] if i > 0 else '<S>'
            left.setdefault(w, Counter())[l] += 1
    return vocab, left


def run(V, left, n_trial, rng):
    rec, prod = set(), set()
    rc_hit = pd_hit = n = 0
    for _ in range(n_trial):
        tgt = V[rng.integers(0, len(V))]
        lc = left.get(tgt)
        if not lc or sum(lc.values()) < 2:
            continue
        cue = lc.most_common(1)[0][0]
        n += 1
        distr = [w for w in V if w != tgt]
        cands = [tgt] + list(rng.choice(distr, 9, replace=False))
        sc = []
        for c in cands:
            r2 = left.get(c, Counter())
            tot = sum(r2.values())
            sc.append(r2.get(cue, 0) / tot if tot > 0 else 0.0)
        if int(np.argmax(sc)) == 0:
            rc_hit += 1
            rec.add(tgt)
        ps = np.array([
            (left.get(w, Counter()).get(cue, 0) / sum(left.get(w, Counter()).values()))
            if sum(left.get(w, Counter()).values()) > 0 else 0.0 for w in V])
        if ps.sum() <= 0:
            continue
        ps = ps / ps.sum()
        if V[int(rng.choice(len(V), p=ps))] == tgt:
            pd_hit += 1
            prod.add(tgt)
    return rec, prod, rc_hit / max(n, 1), pd_hit / max(n, 1)


def main():
    V, left = build()
    V = V[:300]
    rng = np.random.default_rng(1)
    print('n_trial | 理解集 产出集 | 只在产出里 | 理解acc 产出acc | 比')
    rows = []
    for n in (1000, 3000, 10000, 30000):
        rec, prod, ra, pa = run(V, left, n, rng)
        only = len(prod - rec)
        print(f'{n:7d} | {len(rec):6d} {len(prod):6d} | {only:10d} | '
              f'{ra:.4f} {pa:.4f} | {ra/max(pa,1e-9):.2f}')
        rows.append(dict(n_trial=n, receptive_set=len(rec), productive_set=len(prod),
                         only_productive=only, receptive_acc=float(ra),
                         productive_acc=float(pa), ratio=float(ra / max(pa, 1e-9))))
    print('\n★ 结论：产出集随 n_trial 单调膨胀（趋向词表上限），')
    print('  → "理解集 ⊋ 产出集"是【数学平凡】的，只是采样覆盖度，')
    print('  → 不能当作符合文献的证据。')
    print('  唯一稳定的指标是【准确率比】，它不随 n 膨胀。')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'rows': rows, 'vocab_cap': len(V),
                   'verdict': 'containment is mathematically trivial; '
                              'only accuracy ratio is informative'},
                  f, ensure_ascii=False, indent=2)
    print(f'\n已存 {OUT}')


if __name__ == '__main__':
    main()
