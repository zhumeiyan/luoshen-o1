# -*- coding: utf-8 -*-
"""
================================================================
069c · 配对显著性 + 两个检索任务的口径分离
================================================================
069b 出现反转：语义 Top-K 在 K=5/10/20 时【劣于】时间近邻（0.90/0.90/0.99）。
但 050 的结论是：时间分半 0.4340 < 随机 0.5212 < 话题分层 0.5398。
两者方向相反。必须查明是【矛盾】还是【两个不同任务】。

本轮三件事：
  A. 配对显著性：175 个查询上，时间序 vs 语义序的差是否显著（bootstrap + 符号检验）
  B. 口径分离：在同一份数据上同时跑两个任务
       T1 前瞻分半：用编号前 50% 覆盖后 50%（050 的口径）
       T2 近邻检索：取编号最近 K 条召回同实验判据（069b 的口径）
     看结论是否真的相反，还是我算错了
  C. 解释：若两者都对，说明"时间序好不好"取决于【检索范围】——
     大块跨期 vs 局部近邻，是两件不同的事。

运行： python3 experiments/exp069c_task_separation.py
"""
import os
import re
import json
import math
import numpy as np
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT = os.path.join(ROOT, 'result_069c.json')

spec = importlib.util.spec_from_file_location(
    'e069', os.path.join(ROOT, 'experiments', 'exp069_criterion_redundancy.py'))
e069 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e069)

SEED = 20261016
NBOOT = 2000


def main():
    np.random.seed(SEED)
    items = e069.load_items()
    texts = [it['text'] for it in items]
    N = len(items)
    exps = [set(e069.extract_exp(it['text'])) for it in items]
    sims = e069.build_sims(texts)
    S = sims['bigram']

    print('=' * 66)
    print('069c · 配对显著性 + 两个检索任务的口径分离')
    print('=' * 66)

    # ---------------- A 配对显著性 ----------------
    print('\n' + '-' * 66)
    print('A. 时间序 vs 语义序：175 个查询上的配对检验')
    print('-' * 66)
    usable = [i for i in range(N) if exps[i]]
    queries = []
    for i in usable:
        truth = [j for j in usable if j != i and (exps[i] & exps[j])]
        if truth:
            queries.append((i, truth))
    print('  查询数 %d' % len(queries))

    res_a = {}
    for K in (5, 10, 20, 50):
        dt, ds = [], []
        for i, truth in queries:
            tset = set(truth)
            d = np.abs(np.arange(N) - i)
            d[i] = 10 ** 9
            time_sel = list(np.argsort(d)[:K])
            sv = S[i].copy()
            sv[i] = -1
            sem_sel = list(np.argsort(-sv)[:K])
            dt.append(len(tset & set(time_sel)) / len(tset))
            ds.append(len(tset & set(sem_sel)) / len(tset))
        dt, ds = np.array(dt), np.array(ds)
        diff = ds - dt          # 语义 − 时间
        # bootstrap
        idx = np.random.randint(0, len(diff), size=(NBOOT, len(diff)))
        boot = diff[idx].mean(axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        # 符号检验
        npos = int((diff > 0).sum())
        nneg = int((diff < 0).sum())
        from math import comb
        nz = npos + nneg
        # 双侧二项 p（n 小则精确，大则正态近似）
        if nz <= 60:
            k = min(npos, nneg)
            p = min(1.0, 2 * sum(comb(nz, i) for i in range(k + 1)) / (2 ** nz))
        else:
            z = (abs(npos - nz / 2) - 0.5) / np.sqrt(nz / 4)
            p = float(2 * (1 - 0.5 * (1 + math.erf(z / np.sqrt(2)))))
        res_a['K%d' % K] = {
            'time': float(dt.mean()), 'semantic': float(ds.mean()),
            'diff_mean': float(diff.mean()),
            'ci95': [float(lo), float(hi)],
            'n_sem_wins': npos, 'n_time_wins': nneg, 'n_ties': int((diff == 0).sum()),
            'sign_test_p': float(p)}
        verdict = ('语义显著更差' if hi < 0 else
                   ('语义显著更好' if lo > 0 else '无显著差异'))
        print('  K=%-3d 时间 %.4f | 语义 %.4f | 差 %+.4f  CI[%+.4f,%+.4f]  '
              '胜/负=%d/%d  p=%.4g  → %s'
              % (K, dt.mean(), ds.mean(), diff.mean(), lo, hi, npos, nneg, p, verdict))

    # ---------------- B 口径分离：同时跑两个任务 ----------------
    print('\n' + '-' * 66)
    print('B. 口径分离：T1 前瞻分半（050 口径） vs T2 近邻检索（069b 口径）')
    print('-' * 66)

    # T1 前瞻分半：前 50% 条目作为库，后 50% 条目的【实验归属】作为待覆盖目标
    # 050 用的是"覆盖后 50% 的失误"，这里用可比的：后 50% 条目涉及的实验集合，
    # 看前 50% 里有多少实验被覆盖到（召回）
    half = N // 2
    front, back = list(range(half)), list(range(half, N))
    exps_back = set()
    for j in back:
        exps_back |= exps[j]
    exps_front = set()
    for j in front:
        exps_front |= exps[j]
    target = exps_back - exps_front    # 只算后半才出现的新实验（真正的前瞻）
    covered = len(exps_back & exps_front) / (len(exps_back) + 1e-9)
    print('  T1 前瞻分半：前半涉及实验 %d 个，后半涉及 %d 个，'
          '后半中已被前半覆盖 %.4f' % (len(exps_front), len(exps_back), covered))
    print('     （050 的 0.4340 是"旧判据覆盖新失误"的召回，'
          '本处用同口径的实验覆盖度近似复现）')

    # T1 对照：随机分半 / 打乱后分半
    rnds = []
    for _ in range(200):
        perm = np.random.permutation(N)
        f, b = list(perm[:half]), list(perm[half:])
        ef, eb = set(), set()
        for j in f:
            ef |= exps[j]
        for j in b:
            eb |= exps[j]
        rnds.append(len(eb & ef) / (len(eb) + 1e-9))
    rnds = np.array(rnds)
    print('     随机分半覆盖度 %.4f ± %.4f → 时间分半 %s'
          % (rnds.mean(), rnds.std(),
             '劣于随机' if covered < rnds.mean() else '优于随机'))

    # T2 近邻检索（已在 A 跑过，此处取 K=10 与随机对照）
    print('  T2 近邻检索：时间近邻 R@10 = %.4f vs 随机 %.4f （069b）'
          % (res_a['K10']['time'], 0.0633))

    res_b = {'T1_time_half_coverage': float(covered),
             'T1_random_half_mean': float(rnds.mean()),
             'T1_random_half_sd': float(rnds.std()),
             'T1_time_minus_random': float(covered - rnds.mean()),
             'T2_time_K10': res_a['K10']['time'],
             'T2_random_K10': 0.0633}

    # ---------------- C 结论 ----------------
    print('\n' + '-' * 66)
    print('C. 两个任务的方向')
    print('-' * 66)
    t1_dir = '时间 劣于 随机' if covered < rnds.mean() else '时间 优于 随机'
    t2_dir = '时间 优于 随机' if res_a['K10']['time'] > 0.0633 else '时间 劣于 随机'
    print('  T1 前瞻分半（跨越大块时间）: %s  (差 %+.4f)'
          % (t1_dir, covered - rnds.mean()))
    print('  T2 近邻检索（局部小 K）    : %s  (差 %+.4f)'
          % (t2_dir, res_a['K10']['time'] - 0.0633))
    same = (t1_dir == t2_dir)
    print('  → 两者方向 %s' % ('一致（不矛盾）' if same else '【相反】'))
    if not same:
        print('     解释：T1 是"用一半库去覆盖另一半时间段的【新】失误"，'
              '时间分半把同实验的判据切到同一侧或两侧都损失；')
        print('           T2 是"取局部近邻"，同批追加的判据编号相邻，'
              '时间序天然命中。')
        print('     ⇒ 时间序的价值取决于检索范围：局部近邻=强先验，'
              '大块跨期=最差切分。')

    out = {'A_paired': res_a, 'B_tasks': res_b,
           'C_directions_same': bool(same)}
    with open(RESULT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('\n已写出: %s' % RESULT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
