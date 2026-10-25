# -*- coding: utf-8 -*-
"""
================================================================
069b · 检索评价：阈值敏感性 + 用独立真值做真正的检索对比
================================================================
069 留下两个必须回答的质疑：
  Q1 P2 的"连续50条只有20条新信息"是不是 95 分位阈值造成的 artifact？
  Q2 P3 说"到达时冗余仅 2%"，P1 说"相邻相似度是随机 3.37 倍"——两者矛盾吗？

本轮补两块：
  A. 阈值敏感性：把冗余阈值从 50 分位扫到 99.9 分位，看 P2 结论是否稳健。
  B. 真正的检索评价（真值独立于文本相似度）：
       查询 = 一条判据；真值 = 与它【同实验编号】的其他判据
       （实验编号来自正文里的 3 位数字，与文本语义、与编号顺序都无关）
       策略 A 时间序：取编号最近的 K 条
       策略 B 语义序：取相似度 Top-K
       策略 C 随机  ：基线
     指标 recall@K / precision@K。
     策略 B 若胜出，则"按语义重组检索结构"确有增益，且不是循环论证。

运行： python3 experiments/exp069b_retrieval_eval.py
"""
import os
import re
import json
import numpy as np
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT = os.path.join(ROOT, 'result_069b.json')

spec = importlib.util.spec_from_file_location(
    'e069', os.path.join(ROOT, 'experiments', 'exp069_criterion_redundancy.py'))
e069 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e069)

SEED = 20261016


def main():
    np.random.seed(SEED)
    items = e069.load_items()
    texts = [it['text'] for it in items]
    N = len(items)
    exps = [set(e069.extract_exp(it['text'])) for it in items]
    sims = e069.build_sims(texts)
    S = sims['bigram']
    allv = S[np.triu_indices(N, 1)]

    print('=' * 66)
    print('069b · 阈值敏感性 + 独立真值下的检索评价')
    print('=' * 66)
    print('条目 %d ；可提取实验编号 %d' % (N, sum(1 for e in exps if e)))

    # ---------------- A 阈值敏感性 ----------------
    print('\n' + '-' * 66)
    print('A. P2 的阈值敏感性（冗余率是否只是低阈值的 artifact）')
    print('-' * 66)
    print('  %-10s %-10s %-16s %-16s' % ('分位', '阈值', '连续50条新信息', '冗余率'))
    rows = []
    for q in (50, 75, 90, 95, 99, 99.5, 99.9):
        thr = float(np.percentile(allv, q))
        cont = []
        for s in range(0, N - 50 + 1):
            sel = list(range(s, s + 50))
            cont.append(e069.count_novel(sel, S, thr))
        c = float(np.mean(cont))
        rows.append({'percentile': q, 'threshold': thr,
                     'cont50_novel': c, 'redundancy_rate': 1 - c / 50})
        print('  %-10s %-10.4f %-16.2f %-16.1f%%'
              % ('p%s' % q, thr, c, 100 * (1 - c / 50)))

    # ---------------- B 独立真值的检索评价 ----------------
    print('\n' + '-' * 66)
    print('B. 检索评价（真值 = 同实验归属，与文本相似度、与编号顺序均无关）')
    print('-' * 66)
    usable = [i for i in range(N) if exps[i]]
    # 只保留"真值非空"的查询：至少有一个其他条目与之同实验
    queries = []
    for i in usable:
        truth = [j for j in usable if j != i and (exps[i] & exps[j])]
        if truth:
            queries.append((i, truth))
    print('  可用查询数: %d （平均真值集 %.1f 条）'
          % (len(queries), np.mean([len(t) for _, t in queries])))

    out = {'threshold_sensitivity': rows, 'retrieval': {}}
    print('\n  %-6s %-12s %-12s %-12s %-12s' % ('K', '时间序R@K', '语义序R@K', '随机R@K', '语义/时间'))
    for K in (5, 10, 20, 50):
        rt, rs, rr = [], [], []
        for i, truth in queries:
            # 时间序：编号位置最近的 K 条
            d = np.abs(np.arange(N) - i)
            d[i] = 10 ** 9
            time_sel = list(np.argsort(d)[:K])
            # 语义序：相似度 Top-K
            sv = S[i].copy()
            sv[i] = -1
            sem_sel = list(np.argsort(-sv)[:K])
            # 随机
            rnd_sel = list(np.random.choice([x for x in range(N) if x != i],
                                            min(K, N - 1), replace=False))
            tset = set(truth)
            rt.append(len(tset & set(time_sel)) / len(tset))
            rs.append(len(tset & set(sem_sel)) / len(tset))
            rr.append(len(tset & set(rnd_sel)) / len(tset))
        rt, rs, rr = np.mean(rt), np.mean(rs), np.mean(rr)
        out['retrieval']['K%d' % K] = {
            'time_order_recall': float(rt), 'semantic_recall': float(rs),
            'random_recall': float(rr),
            'ratio_semantic_over_time': float(rs / (rt + 1e-9))}
        print('  %-6d %-12.4f %-12.4f %-12.4f %-12.2f' % (K, rt, rs, rr, rs / (rt + 1e-9)))

    # ---------------- C 解释 P1 与 P3 的张力 ----------------
    print('\n' + '-' * 66)
    print('C. P1（相邻=随机×3.37）与 P3（到达时冗余仅2%）为何不矛盾')
    print('-' * 66)
    adj = np.array([S[i, i + 1] for i in range(N - 1)])
    print('  相邻相似度分布: 均值 %.4f | 中位 %.4f | 90分位 %.4f | 最大 %.4f'
          % (adj.mean(), np.median(adj), np.percentile(adj, 90), adj.max()))
    print('  P3 用的"冗余"阈值 = 0.30 / 0.50 / 0.70')
    for thr in (0.30, 0.50, 0.70):
        print('    → 相邻对中超过 %.2f 的: %d / %d (%.1f%%)'
              % (thr, int((adj >= thr).sum()), len(adj), 100 * (adj >= thr).mean()))
    print('  结论：相邻【更相似】是相对的（×3.37），但【未达重复】是绝对的')
    print('        → 069 的 Q21 声称"相邻十条讲同一件事"属于夸大，本轮修正')

    out['tension'] = {
        'adjacent_mean': float(adj.mean()),
        'adjacent_median': float(np.median(adj)),
        'adjacent_p90': float(np.percentile(adj, 90)),
        'adjacent_max': float(adj.max()),
        'frac_adj_ge_030': float((adj >= 0.30).mean()),
        'frac_adj_ge_050': float((adj >= 0.50).mean()),
    }

    with open(RESULT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('\n已写出: %s' % RESULT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
