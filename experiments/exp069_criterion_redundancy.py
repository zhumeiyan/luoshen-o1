# -*- coding: utf-8 -*-
"""
================================================================
069 · 判据核的检索结构：只增不减是否制造了冗余
================================================================
缘起：
  068 的模拟答辩 Q21（"186 条怎么检索"）里，我们自曝：
    判据核只增不减 → 检索结构退化成时间序 → 相邻十条讲同一件事
    → 按编号取库覆盖度 0.4340，还不如随机抽样。
  那是一个【声称】，没有任何实验测过它。本实验把它变成可测命题。

四个命题：
  P1 时间序冗余：编号相邻的条目，是否显著比随机条目对更相似？
  P2 检索效率：连续取 K 条 vs 语义去重取 K 条，独立信息量差多少？
  P3 成因：只增不减 vs 允许修订，模拟对照下冗余率差多少？
  P4 独立真值：文本相似度能否预测"同实验归属"（与文本无关的结构真值）？

反偏见设计（本实验最大的风险是自己给自己打分）：
  · P1 用【三重独立度量】交叉：字符 bigram / unigram TF-IDF 余弦 / 实词 Jaccard。
    三者粒度不同，若结论一致则不是单一表示的 artifact。
  · 负对照 N1：条目文本在条目间随机重排（集合不变、配对破坏）→ 相邻相似度应塌到随机水平。
  · 负对照 N2：每条判据内部字符打乱（保字符分布、毁语序）→ 相似度应显著下降，
    证明度量在测"怎么写的"而不只是"用了哪些字"。
  · P4 是与文本【完全独立】的真值（同实验归属），用于证明相似度确实在测语义。

运行： python3 experiments/exp069_criterion_redundancy.py
"""
import os
import re
import json
import random
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'evidence', '失败模式库', '判据核.md')
OUT = os.path.join(ROOT, 'result_069.json')

DEF_RE = re.compile(r'^第\s*(\d+)\s*条')
SEED = 20261016

# ---------------------------------------------------------------- 提取
def parse_def(line):
    s = line.strip().lstrip('-•').strip().lstrip('#').strip().lstrip('*').strip()
    m = DEF_RE.match(s)
    return int(m.group(1)) if m else None


def load_items():
    with open(PATH, encoding='utf-8') as f:
        lines = f.read().split('\n')
    defs = []
    for i, line in enumerate(lines):
        n = parse_def(line)
        if n is not None:
            defs.append((n, i, line.strip().lstrip('-•#*').strip()))
    items = []
    for k, (n, i, title) in enumerate(defs):
        end = defs[k + 1][1] if k + 1 < len(defs) else min(i + 14, len(lines))
        body = '\n'.join(lines[i + 1:end])
        body = re.sub(r'[#*`>\-\|]', ' ', body)
        body = re.sub(r'\s+', ' ', body).strip()
        items.append({'num': n, 'title': title, 'body': body,
                      'text': (title + ' ' + body).strip()})
    # 同编号去重（保留首次）
    seen, uniq = set(), []
    for it in items:
        if it['num'] in seen:
            continue
        seen.add(it['num'])
        uniq.append(it)
    uniq.sort(key=lambda x: x['num'])
    return uniq


def extract_exp(text):
    """所属实验：正文/标题里出现的 3 位实验编号（与文本语义无关的结构真值）。"""
    m = re.findall(r'(?<![0-9])(\d{3})(?![0-9])', text)
    return sorted(set(m))


# ---------------------------------------------------------------- 相似度
def char_ngrams(s, n):
    s = re.sub(r'\s+', '', s)
    if len(s) < n:
        return [s] if s else []
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def tfidf_matrix(docs, n):
    vocab = {}
    rows = []
    for d in docs:
        grams = char_ngrams(d, n)
        cnt = {}
        for g in grams:
            cnt[g] = cnt.get(g, 0) + 1
        rows.append(cnt)
        for g in cnt:
            if g not in vocab:
                vocab[g] = len(vocab)
    N = len(docs)
    M = np.zeros((N, len(vocab)))
    df = np.zeros(len(vocab))
    for i, cnt in enumerate(rows):
        for g, c in cnt.items():
            j = vocab[g]
            M[i, j] = c
            df[j] += 1
    # tf-idf + L2
    idf = np.log((N + 1) / (df + 1)) + 1.0
    M = M * idf
    norm = np.linalg.norm(M, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return M / norm


STOP = set('的了是在和与及或不而其对为以将于中被把给从到有个这那些我你它我们你们它们'
           '会要能可将只也很都就还又再没无有做用使让让令则若如但并且以及之时之后'
           '一二三四五六七八九十第条项种类型问题现象判据实验条件结果数据值数组'
           '本轮首版实测因此所以因为由于导致造成出现产生发生进行通过对于关于')


def word_set(s):
    # 中文按字切（无 jieba），取非停用字 + 英文/数字 token
    toks = set()
    for ch in s:
        if '\u4e00' <= ch <= '\u9fff' and ch not in STOP:
            toks.add(ch)
    for w in re.findall(r'[A-Za-z][A-Za-z_\-\.]{1,}|[0-9]{2,}', s):
        toks.add(w.lower())
    return toks


def build_sims(texts):
    """返回三种独立相似度矩阵。"""
    out = {}
    for name, n in (('bigram', 2), ('unigram', 1)):
        M = tfidf_matrix(texts, n)
        out[name] = M @ M.T
    # Jaccard（实词集合）
    ws = [word_set(t) for t in texts]
    N = len(ws)
    J = np.zeros((N, N))
    for i in range(N):
        for j in range(i, N):
            a, b = ws[i], ws[j]
            inter = len(a & b)
            union = len(a | b) or 1
            J[i, j] = J[j, i] = inter / union
    out['jaccard'] = J
    return out


# ---------------------------------------------------------------- 主实验
def main():
    random.seed(SEED)
    np.random.seed(SEED)
    items = load_items()
    texts = [it['text'] for it in items]
    N = len(items)
    print('=' * 66)
    print('069 · 判据核检索结构：只增不减是否制造冗余')
    print('=' * 66)
    print('条目数（去重后）: %d   编号范围: %d - %d' % (N, items[0]['num'], items[-1]['num']))
    if N < 30:
        print('[FAIL] 条目不足，无法统计')
        return 1
    print('平均文本长度: %.0f 字' % np.mean([len(t) for t in texts]))

    sims = build_sims(texts)
    res = {'n_items': N, 'seed': SEED}

    # ---------------- P1 时间序冗余 ----------------
    print('\n' + '-' * 66)
    print('P1 时间序冗余：编号相邻 vs 随机配对')
    print('-' * 66)
    p1 = {}
    for name, S in sims.items():
        iu = np.triu_indices(N, 1)
        allv = S[iu]
        # 相邻（编号连续差 <= d）
        adj_idx = [(i, i + 1) for i in range(N - 1)]
        adj = np.array([S[i, j] for i, j in adj_idx])
        # 近邻窗口 |i-j| <= 5
        near = [(i, j) for i in range(N) for j in range(i + 1, min(i + 6, N))]
        nearv = np.array([S[i, j] for i, j in near])
        # 随机配对（多次重采样给分布）
        rnds = []
        for _ in range(200):
            perm = np.random.permutation(N)
            rnds.append(np.mean([S[perm[i], perm[i + 1]] for i in range(N - 1)]))
        rnds = np.array(rnds)
        d = adj.mean() - rnds.mean()
        t = d / (rnds.std() + 1e-12)
        p1[name] = {
            'adjacent_mean': float(adj.mean()),
            'near5_mean': float(nearv.mean()),
            'all_pairs_mean': float(allv.mean()),
            'random_pair_mean': float(rnds.mean()),
            'random_pair_sd': float(rnds.std()),
            'delta_adj_minus_random': float(d),
            't_like': float(t),
            'ratio_adj_over_random': float(adj.mean() / (rnds.mean() + 1e-12)),
        }
        print('  [%s] 相邻 %.4f | 窗口5 %.4f | 全部对 %.4f | 随机 %.4f±%.4f  '
              '→ Δ=%+.4f (t=%+.2f, ×%.2f)'
              % (name, adj.mean(), nearv.mean(), allv.mean(),
                 rnds.mean(), rnds.std(), d, t,
                 adj.mean() / (rnds.mean() + 1e-12)))
    res['P1_time_order_redundancy'] = p1

    # ---------------- 负对照 N1：条目文本在条目间重排 ----------------
    print('\n' + '-' * 66)
    print('负对照 N1：文本在条目间随机重排（集合不变，配对破坏）')
    print('-' * 66)
    n1 = {}
    for name in sims:
        vals = []
        for _ in range(20):
            perm = list(range(N))
            random.shuffle(perm)
            shuf = [texts[p] for p in perm]
            S2 = build_sims(shuf)[name]
            vals.append(np.mean([S2[i, i + 1] for i in range(N - 1)]))
        n1[name] = {'shuffled_adjacent_mean': float(np.mean(vals)),
                    'shuffled_sd': float(np.std(vals)),
                    'original_adjacent_mean': p1[name]['adjacent_mean']}
        print('  [%s] 原相邻 %.4f → 重排后 %.4f±%.4f  %s'
              % (name, p1[name]['adjacent_mean'], np.mean(vals), np.std(vals),
                 '✓ 塌到随机（冗余来自配对本身）'
                 if np.mean(vals) < p1[name]['adjacent_mean'] else '✗ 未塌'))
    res['N1_shuffle_items'] = n1

    # ---------------- 负对照 N2：判据内部字符打乱 ----------------
    print('\n' + '-' * 66)
    print('负对照 N2：每条判据内部字符打乱（保字符分布，毁语序）')
    print('-' * 66)
    n2 = {}
    for name in ('bigram', 'unigram'):  # jaccard 是集合，不受语序影响，不适用
        vals = []
        for _ in range(20):
            mangled = []
            for t in texts:
                cs = list(t)
                random.shuffle(cs)
                mangled.append(''.join(cs))
            S2 = build_sims(mangled)[name]
            vals.append(np.mean([S2[i, i + 1] for i in range(N - 1)]))
        n2[name] = {'mangled_adjacent_mean': float(np.mean(vals)),
                    'original_adjacent_mean': p1[name]['adjacent_mean']}
        print('  [%s] 原相邻 %.4f → 字符打乱 %.4f  %s'
              % (name, p1[name]['adjacent_mean'], np.mean(vals),
                 '✓ 显著下降（度量在测语序/语义，不只是字符）'
                 if np.mean(vals) < p1[name]['adjacent_mean'] * 0.7 else '✗ 未下降'))
    res['N2_mangle_chars'] = n2

    # ---------------- P2 检索效率：连续 K 条 vs 语义去重 K 条 ----------------
    print('\n' + '-' * 66)
    print('P2 检索效率：连续取 K 条 vs 语义去重取 K 条')
    print('-' * 66)
    S = sims['bigram']
    # 阈值：用全部配对相似度的某个高分位
    allv = S[np.triu_indices(N, 1)]
    thr = float(np.percentile(allv, 95))
    print('  冗余判定阈值（全部配对 95 分位）= %.4f' % thr)
    p2 = {'threshold': thr, 'rows': []}
    print('  %-8s %-14s %-14s %-10s' % ('K', '连续K条新信息', '去重K条新信息', '提升'))
    for K in (10, 20, 30, 50, 100):
        if K > N:
            continue
        # 连续取：从每个起点滑窗，平均"新信息条数"
        cont = []
        for s in range(0, N - K + 1):
            sel = list(range(s, s + K))
            cont.append(count_novel(sel, S, thr))
        # 语义去重取：贪心，从编号 0 扫， dissimilar 才收，直到收满 K 条
        dedup_sel = greedy_dedup(S, thr, K, N)
        dedup_novel = count_novel(dedup_sel, S, thr)
        c = float(np.mean(cont))
        row = {'K': K, 'contiguous_novel': c, 'dedup_novel': float(dedup_novel),
               'gain': float(dedup_novel - c)}
        p2['rows'].append(row)
        print('  %-8d %-14.2f %-14.2f %-10s'
              % (K, c, dedup_novel,
                 ('+%d (×%.2f)' % (dedup_novel - c, dedup_novel / (c + 1e-9)))
                 if c > 0 else 'n/a'))
    res['P2_retrieval_efficiency'] = p2

    # ---------------- P4 独立真值：同实验归属 ----------------
    print('\n' + '-' * 66)
    print('P4 独立真值：文本相似度能否预测「同实验归属」')
    print('-' * 66)
    exps = [set(extract_exp(it['text'])) for it in items]
    n_with = sum(1 for e in exps if e)
    print('  可提取到实验编号的条目: %d / %d' % (n_with, N))
    p4 = {}
    if n_with >= 20:
        y, scores = [], {}
        for name, S in sims.items():
            scores[name] = []
        for i in range(N):
            for j in range(i + 1, N):
                if not exps[i] or not exps[j]:
                    continue
                y.append(1 if (exps[i] & exps[j]) else 0)
                for name in scores:
                    scores[name].append(sims[name][i, j])
        y = np.array(y)
        print('  配对数 %d，同实验正例 %d (%.1f%%)' % (len(y), y.sum(), 100 * y.mean()))
        if 0 < y.sum() < len(y):
            for name in scores:
                s = np.array(scores[name])
                auc = roc_auc(y, s)
                mp = s[y == 1].mean()
                mn = s[y == 0].mean()
                p4[name] = {'auc': auc, 'mean_pos': float(mp), 'mean_neg': float(mn),
                            'n_pairs': int(len(y)), 'n_pos': int(y.sum())}
                print('  [%s] 同实验 %.4f vs 异实验 %.4f  → AUC %.3f %s'
                      % (name, mp, mn, auc,
                         '✓ 相似度确实在测语义' if auc > 0.6 else
                         ('— 接近随机' if 0.45 <= auc <= 0.6 else '✗ 反向')))
        else:
            print('  [跳过] 正负例不均衡，无法算 AUC')
    else:
        print('  [跳过] 可提取实验编号的条目太少')
    res['P4_independent_truth'] = p4

    # ---------------- P3 成因：只增不减 vs 允许修订 ----------------
    print('\n' + '-' * 66)
    print('P3 成因：只增不减 vs 允许修订（按真实编号顺序回放）')
    print('-' * 66)
    p3 = {}
    for thr_r in (0.30, 0.50, 0.70):
        append_n, revise_n = N, 0
        live = []          # 已入库条目索引
        redundant_seen = 0
        for i in range(N):
            if live:
                mx = max(S[i, j] for j in live)
            else:
                mx = 0.0
            if mx >= thr_r:
                redundant_seen += 1
                revise_n += 1      # 允许修订时不新增
            else:
                append_n += 0
            live.append(i)
        # 只增不减：库大小恒为 N；修订制：库大小 = N - redundant_seen
        p3['thr_%.2f' % thr_r] = {
            'append_only_size': N,
            'revise_allowed_size': N - redundant_seen,
            'redundant_on_arrival': redundant_seen,
            'redundant_frac': redundant_seen / N,
        }
        print('  阈值 %.2f → 到达时即与已有条目冗余的: %d / %d (%.1f%%)；'
              '只增不减库 %d 条 vs 可修订库 %d 条'
              % (thr_r, redundant_seen, N, 100 * redundant_seen / N,
                 N, N - redundant_seen))
    res['P3_cause'] = p3

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print('\n已写出: %s' % OUT)
    return 0


def count_novel(sel, S, thr):
    """选中集合里，彼此不冗余的条数（贪心）。"""
    kept = []
    for i in sel:
        if all(S[i, j] < thr for j in kept):
            kept.append(i)
    return len(kept)


def greedy_dedup(S, thr, K, N):
    """按编号扫，收集 K 条彼此不冗余的条目。"""
    kept = []
    for i in range(N):
        if len(kept) >= K:
            break
        if all(S[i, j] < thr for j in kept):
            kept.append(i)
    # 不足则宽松补
    for i in range(N):
        if len(kept) >= K:
            break
        if i not in kept:
            kept.append(i)
    return kept


def roc_auc(y, s):
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float('nan')
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    return float((ranks[y == 1].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


if __name__ == '__main__':
    raise SystemExit(main())
