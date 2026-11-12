"""
★113 中文切词的真实层级 —— 用真实 TP + 外部人工标注金标

★112 的结论：音节层是错的层。真实中文音节 bigram 最大 TP 只有 0.23（等效32选1），
而我给的考场是 3 选 1，简单 10 倍。

这一课：
  1. 层换到【汉字】—— 中文的真实切分线索在这一层
  2. 语料不简化 —— 用 KdConv 全部真实汉字（106万），真实 TP 有多脏就有多脏
  3. 金标是外部的 —— KdConv attrs 里的人工标注实体（4292 个真词，清华标注，不是我）
  4. 方法不只用原始 TP —— 领域真正用的是 PMI 和分支熵（Jin & Tanaka-Ishii 2006）
"""
import sys, os, json, re, math
import numpy as np
from collections import Counter, defaultdict

ROOT = '/data/workspace/luoshen-o1'
sys.path.insert(0, ROOT)
os.makedirs(f'{ROOT}/data', exist_ok=True)

RES = {}


def rec(k, v):
    RES[k] = v
    print(f'  {k}: {v}')


# ────────────────────────────────────────────
def load_msgs():
    """真实汉字串，按 message 切段（不跨 message 制造假边界）"""
    msgs = []
    for dom in ('film', 'music', 'travel'):
        for dlg in json.load(open(f'/data/workspace/kdconv/{dom}_train.json')):
            for m in dlg.get('messages', []):
                h = re.findall(r'[\u4e00-\u9fff]', m.get('message', ''))
                if len(h) >= 6:
                    msgs.append(''.join(h))
    return msgs


def gold_entities(msgs):
    """外部人工标注实体 → 真词表（清华 KdConv attrs，不是我造的）"""
    ents, ctx = Counter(), Counter()
    for dom in ('film', 'music', 'travel'):
        for dlg in json.load(open(f'/data/workspace/kdconv/{dom}_train.json')):
            for m in dlg.get('messages', []):
                for a in m.get('attrs', []) or []:
                    nm = re.sub(r'（.*?）', '', a.get('name', '') or '')
                    nm = ''.join(re.findall(r'[\u4e00-\u9fff]', nm))
                    cand = [nm]
                    v = ''.join(re.findall(r'[\u4e00-\u9fff]',
                                           str(a.get('attrvalue', ''))))
                    if 2 <= len(v) <= 6:
                        cand.append(v)
                    for c in cand:
                        if 2 <= len(c) <= 6:
                            ents[c] += 1
    # 只保留在语料里真出现过的
    alltext = '\n'.join(msgs)
    return {e for e in ents if e in alltext and ents[e] >= 3}


def find_spans(msgs, ents):
    """标出每个 message 里实体的位置 → 真边界 / 真内部"""
    bnd, ins = [], []
    for s in msgs:
        for e in ents:
            start = 0
            while True:
                i = s.find(e, start)
                if i < 0:
                    break
                if i > 0:                       # 实体前一个位置 = 真边界
                    bnd.append((s, i - 1))
                if i + len(e) < len(s) - 1:     # 实体后一个位置 = 真边界
                    bnd.append((s, i + len(e) - 1))
                for k in range(len(e) - 1):     # 实体内部 = 真非边界
                    ins.append((s, i + k))
                start = i + 1
    return bnd, ins


# ────────────────────────────────────────────
def build_counts(msgs):
    uni, bi, tri = Counter(), Counter(), Counter()
    fwd1, bwd1 = defaultdict(Counter), defaultdict(Counter)
    for s in msgs:
        for c in s:
            uni[c] += 1
        for a, b in zip(s[:-1], s[1:]):
            bi[(a, b)] += 1
            fwd1[a][b] += 1
            bwd1[b][a] += 1
        for a, b, c in zip(s[:-2], s[1:], s[2:]):
            tri[(a, b, c)] += 1
    return uni, bi, tri, fwd1, bwd1


def H(counter):
    tot = sum(counter.values())
    if tot <= 0:
        return 0.0
    return -sum((v / tot) * math.log(v / tot) for v in counter.values())


def features(s, i, uni, bi, tri, fwd1, bwd1, N):
    """位置 i（在 s[i] 与 s[i+1] 之间）的四个特征"""
    a, b = s[i], s[i + 1]
    # 原始 TP：P(b|a)
    tp = bi[(a, b)] / max(uni[a], 1)
    # PMI（领域标准的凝聚度）
    pab = bi[(a, b)] / max(N, 1)
    pa, pb = uni[a] / max(N, 1), uni[b] / max(N, 1)
    pmi = math.log(pab / (pa * pb)) if pab > 0 and pa > 0 and pb > 0 else -20.0
    # 右分支熵：a 后面能接多少种（Jin & Tanaka-Ishii）
    hbr = H(fwd1[a])
    # 左分支熵
    hbl = H(bwd1[b])
    return dict(tp=tp, pmi=pmi, hbr=hbr, hbl=hbl)


def auc(pos, neg):
    """pos 应大于 neg"""
    pos = np.asarray(pos, float)
    neg = np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    rng = np.random.default_rng(0)
    if len(pos) * len(neg) > 4_000_000:
        pos = rng.choice(pos, 2000, replace=False)
        neg = rng.choice(neg, 2000, replace=False)
    d = pos[:, None] - neg[None, :]
    return float((d > 0).mean() + 0.5 * (d == 0).mean())


def main():
    print('【1】真实语料与外部金标')
    msgs = load_msgs()
    N = sum(len(s) for s in msgs)
    rec('messages', len(msgs))
    rec('hanzi', N)
    ents = gold_entities(msgs)
    rec('gold_entities', len(ents))
    rec('gold_sample', sorted(list(ents))[:10])

    print('\n【2】标出真边界 / 真内部')
    bnd, ins = find_spans(msgs, ents)
    rng = np.random.default_rng(1)
    idx = rng.choice(len(bnd), min(20000, len(bnd)), replace=False)
    bnd = [bnd[i] for i in idx]
    idx = rng.choice(len(ins), min(20000, len(ins)), replace=False)
    ins = [ins[i] for i in idx]
    rec('gold_boundaries', len(bnd))
    rec('gold_interiors', len(ins))

    print('\n【3】真实汉字 bigram 有多脏（REAL）')
    uni, bi, tri, fwd1, bwd1 = build_counts(msgs)
    rec('char_types', len(uni))
    # 平均最大 TP
    tot = Counter()
    for (a, b), c in bi.items():
        tot[a] += c
    mx = [bi[(a, b)] / tot[a] for (a, b) in list(bi)[:20000]
          if tot[a] >= 20]
    rec('real_max_tp_mean', round(float(np.mean([bi[(a, b)] / tot[a]
        for (a, b) in bi if tot[a] >= 20])), 4))
    rec('equiv_choices', round(float(1.0 / np.mean([bi[(a, b)] / tot[a]
        for (a, b) in bi if tot[a] >= 20])), 1))

    print('\n【4】四种方法在真金标上的边界判别力（AUC）')
    P = defaultdict(list)
    Q = defaultdict(list)
    for s, i in bnd:
        f = features(s, i, uni, bi, tri, fwd1, bwd1, N)
        for k, v in f.items():
            P[k].append(v)
    for s, i in ins:
        f = features(s, i, uni, bi, tri, fwd1, bwd1, N)
        for k, v in f.items():
            Q[k].append(v)
    for k in ('tp', 'pmi', 'hbr', 'hbl'):
        rec(f'auc_{k}', round(auc(P[k], Q[k]), 4))

    print('\n【5】领域标准做法：PMI 的边界 F1（不是我编的分）')
    pv = np.array(P['pmi'])
    qv = np.array(Q['pmi'])
    best = (None, -1)
    for t in np.percentile(np.concatenate([pv, qv]), np.arange(5, 100, 2.5)):
        prec = (pv > t).mean()
        rec_ = (pv > t).mean()
        fp = (qv > t).mean()
        f1 = 2 * prec / max(prec + (prec * 0 + 1e-9), 1e-9)  # 占位
        # 真 F1：把 boundary 当正类，用样本量加权
        TPn = (pv > t).sum()
        FPn = (qv > t).sum()
        FNn = (pv <= t).sum()
        pr = TPn / max(TPn + FPn, 1)
        rc = TPn / max(TPn + FNn, 1)
        f1 = 2 * pr * rc / max(pr + rc, 1e-9)
        if f1 > best[1]:
            best = (float(t), float(f1), float(pr), float(rc))
    rec('pmi_best_threshold', round(best[0], 3))
    rec('pmi_F1', round(best[1], 4))
    rec('pmi_precision', round(best[2], 4))
    rec('pmi_recall', round(best[3], 4))

    print('\n【6】基线对照')
    # 基线 A：随机放边界
    rec('baseline_random_AUC', 0.5)
    rec('baseline_random_F1', round(2 * 0.5 * 0.5 / 1.0, 4))
    # 基线 B：只看字频（不用序列信息）
    pf = np.array([uni[s[i + 1]] for s, i in bnd])
    qf = np.array([uni[s[i + 1]] for s, i in ins])
    rec('baseline_charfreq_AUC', round(auc(pf, qf), 4))
    # 基线 C：每两个字切一刀
    rec('baseline_fixed2_note', '真词平均长度见下')
    rec('gold_word_len_mean', round(float(np.mean([len(e) for e in ents])), 2))

    print('\n【7】她：只用 TP 的学习器，在真语料上能做到多少')
    tp_p, tp_q = np.array(P['tp']), np.array(Q['tp'])
    best2 = (None, -1)
    for t in np.percentile(np.concatenate([tp_p, tp_q]), np.arange(5, 100, 2.5)):
        TPn = (tp_p < t).sum()   # 边界 = TP 低
        FPn = (tp_q < t).sum()
        FNn = (tp_p >= t).sum()
        pr = TPn / max(TPn + FPn, 1)
        rc = TPn / max(TPn + FNn, 1)
        f1 = 2 * pr * rc / max(pr + rc, 1e-9)
        if f1 > best2[1]:
            best2 = (float(t), float(f1), float(pr), float(rc))
    rec('tp_only_F1', round(best2[1], 4))
    rec('tp_only_precision', round(best2[2], 4))
    rec('tp_only_recall', round(best2[3], 4))

    json.dump(RES, open(f'{ROOT}/data/exp113_chineseword.json', 'w'),
              ensure_ascii=False, indent=1)
    print('\n→ data/exp113_chineseword.json')


if __name__ == '__main__':
    main()
