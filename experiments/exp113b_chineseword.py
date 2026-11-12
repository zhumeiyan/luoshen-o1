"""★113b 修正：方向、随机基线、金标偏差检验

★113 有两个错：
  1) PMI / TP 的判别方向我判反了（AUC 0.11 = 反向 0.89，我按正向算了 F1）
  2) 随机基线算错了（我写 2*0.5*0.5=0.5，那不是随机）

还有一个更深的怀疑必须查：
  金标边界全都紧贴实体（专名），内部位置全在实体内（高凝聚）。
  → 这个对比可能人为偏易。要加一个【非实体内部位置】做对照。
"""
import sys, os, json, re, math
import numpy as np
from collections import Counter, defaultdict

ROOT = '/data/workspace/luoshen-o1'
sys.path.insert(0, ROOT)
from experiments.exp113_chineseword import (load_msgs, gold_entities,
                                            build_counts, features, auc, H)

RES = {}


def rec(k, v):
    RES[k] = v
    print(f'  {k}: {v}')


def f1_at(scores_pos, scores_neg, lower_is_boundary=True):
    """扫阈值求最佳 F1（正类 = 边界）"""
    p = np.asarray(scores_pos, float)
    q = np.asarray(scores_neg, float)
    best = (None, -1, 0, 0)
    lo, hi = min(p.min(), q.min()), max(p.max(), q.max())
    for t in np.linspace(lo, hi, 60):
        if lower_is_boundary:
            TPn, FPn = (p < t).sum(), (q < t).sum()
        else:
            TPn, FPn = (p > t).sum(), (q > t).sum()
        FNn = len(p) - TPn
        pr = TPn / max(TPn + FPn, 1)
        rc = TPn / max(TPn + FNn, 1)
        f1 = 2 * pr * rc / max(pr + rc, 1e-9)
        if f1 > best[1]:
            best = (float(t), float(f1), float(pr), float(rc))
    return best


def main():
    msgs = load_msgs()
    N = sum(len(s) for s in msgs)
    ents = gold_entities(msgs)
    rec('hanzi', N)
    rec('gold_entities', len(ents))

    uni, bi, tri, fwd1, bwd1 = build_counts(msgs)

    # ── 三组位置 ────────────────────────────────
    bnd, ins_ent, ins_rand = [], [], []
    rng = np.random.default_rng(1)
    eset = set()
    for s in msgs:
        for e in ents:
            st = 0
            while True:
                i = s.find(e, st)
                if i < 0:
                    break
                if i > 0:
                    bnd.append((s, i - 1))
                if i + len(e) < len(s) - 1:
                    bnd.append((s, i + len(e) - 1))
                for k in range(len(e) - 1):
                    ins_ent.append((s, i + k))
                    eset.add((id(s), i + k))
                st = i + 1
    # 随机内部位置（不在实体内、不是实体边界）
    bndset = {(id(s), i) for s, i in bnd}
    for s in msgs:
        for i in range(len(s) - 1):
            if (id(s), i) not in eset and (id(s), i) not in bndset:
                ins_rand.append((s, i))
    rec('n_boundary', len(bnd))
    rec('n_inside_entity', len(ins_ent))
    rec('n_random_interior', len(ins_rand))

    def feats(lst, cap=20000):
        idx = rng.choice(len(lst), min(cap, len(lst)), replace=False)
        return [features(lst[i][0], lst[i][1], uni, bi, tri, fwd1, bwd1, N)
                for i in idx]

    B = feats(bnd)
    IE = feats(ins_ent)
    IR = feats(ins_rand)

    print('\n【A】方向修正后的 AUC（边界 vs 随机内部 —— 无偏对照）')
    eff = {}
    for k in ('tp', 'pmi', 'hbr', 'hbl'):
        a = auc([f[k] for f in B], [f[k] for f in IR])
        eff[k] = max(a, 1 - a)
        rec(f'auc_{k}', f'{a:.4f}  → 有效 {eff[k]:.4f} '
                        f'({"边界处更高" if a > 0.5 else "边界处更低"})')

    print('\n【B】金标偏差检验：实体内部 vs 随机内部，难度差多少')
    for k in ('tp', 'pmi', 'hbr'):
        a1 = max(auc([f[k] for f in B], [f[k] for f in IE]),
                 1 - auc([f[k] for f in B], [f[k] for f in IE]))
        rec(f'auc_{k}_vs_entity', round(a1, 4))
        rec(f'auc_{k}_vs_random', round(eff[k], 4))
        rec(f'  inflation_{k}', round(a1 - eff[k], 4))

    print('\n【C】正确方向下的 F1（边界 vs 随机内部）')
    for k, low in (('tp', True), ('pmi', True), ('hbr', False), ('hbl', False)):
        t, f1, pr, rc = f1_at([f[k] for f in B], [f[k] for f in IR], low)
        rec(f'F1_{k}', round(f1, 4))
        rec(f'  P_{k}', round(pr, 4))
        rec(f'  R_{k}', round(rc, 4))

    print('\n【D】真·随机基线（按类比例）')
    rp = rng.random(len(B))
    rq = rng.random(len(IR))
    # 随机猜：以概率 p 判为边界，最优 p 下 F1
    best = max(2 * p_ * 0.999 / (p_ + 0.999) for p_ in np.linspace(0.01, 0.99, 99))
    rec('random_F1_upper', round(float(best), 4))
    rec('note', '随机基线 F1 随猜正比例上升，上界≈1 —— 说明 F1 在类别极不平衡时会骗人')
    rec('boundary_rate_in_real_text', round(len(B) / max(len(B) + len(IR), 1), 4))

    print('\n【E】合并特征（TP 低 + 分支熵高）')
    comb_p = [-f['tp'] + 0.5 * f['hbr'] for f in B]
    comb_q = [-f['tp'] + 0.5 * f['hbr'] for f in IR]
    rec('auc_combined', round(auc(comb_p, comb_q), 4))
    t, f1, pr, rc = f1_at(comb_p, comb_q, False)
    rec('F1_combined', round(f1, 4))

    json.dump(RES, open(f'{ROOT}/data/exp113b_chineseword.json', 'w'),
              ensure_ascii=False, indent=1)
    print('\n→ data/exp113b_chineseword.json')


if __name__ == '__main__':
    main()
