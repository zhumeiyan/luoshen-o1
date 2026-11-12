"""
★91 用自己的度量衡造工具，去理解人的知识符号（代码）

她没有"作用域/模块/类型"这些人的概念。她有的是：
    溯源链（★88）  误差传播（★89）  模糊-精确权衡（★86）
这一课让她用这三件已有工具去量真代码（Python 标准库，真人写的真知识符号）。

核心区分（这一课最重要的一条）：
    "追不到" ≠ "不存在"
    定义是真的，只是超出她的溯源深度。真符号而够不着，和真的空洞符号，
    表现一模一样。她必须靠自己的判断分开，且不许把前者说成后者。

度量衡全部是她自己的（★88）：成本用 t₀，证据强度用 LSB。

判据 12 条。凡是"峰"都要求内部峰（不在网格边界），凡是依赖都做两端对照。
"""

import os
import sys
import json
import random
import sysconfig
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import semiotics as S

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'data', 'exp91_semiotics.json')

BUDGET = 1.2e-7      # 她的预算（t₀）
PENALTY = 0.60       # 超预算惩罚强度
NL_REL = 0.80        # 自然语言线索的真实可靠性（人写注释不一定准）

D_GRID = [1, 2, 3, 4, 6, 8, 12, 16, 20]
BETA_GRID = [0.0, 0.3, 0.6, 0.9, 1.2]
TAU_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
THR_GRID = [0.35, 0.45, 0.50, 0.55, 0.60, 0.65, 0.75]

# 我会凭直觉填的（工程常识：追到底、信注释、中位门槛）
MINE = {'d': 20, 'tau': 1.0, 'thr': 0.50}


H_REF = 0.33          # 训练时的中位空洞率（她自己的经验锚点）
WIN = 40              # 滑动窗口：她用最近的未知率估计当前环境的空洞率
MIN_OBS = 12


def evaluate(tasks, corpus, params, rnd, nl_rel=NL_REL, penalty=PENALTY,
             budget=BUDGET, external=True):
    """
    params 含 beta 时启用"规则模式"：
        thr = thr0 + beta * (ĥ − H_REF)
    其中 ĥ 是她自己最近测到的未知率 —— 她能观测的量，不需要外部告知空洞率。
    beta=0 退化为"记住一个固定门槛"（记忆派）。
    """
    tot = 0.0
    st = {'fp': 0, 'fn': 0, 'unk': 0, 'spent': 0.0,
          'unk_true_recall': 0, 'unk_hole_pass': 0, 'n_unk_true': 0, 'n_unk_hole': 0}
    thr0 = params.get('thr0', params.get('thr', 0.5))
    beta = params.get('beta', 0.0)
    hist = []
    for t in tasks:
        if beta != 0.0 and len(hist) >= MIN_OBS:
            h_hat = sum(hist[-WIN:]) / len(hist[-WIN:])
        else:
            h_hat = H_REF
        eff = {'d': params['d'], 'tau': params['tau'],
               'thr': max(0.05, min(0.95, thr0 + beta * (h_hat - H_REF)))}
        cl, cost, u = S.decide(t['name'], t['ctx'], t['home'], corpus, eff,
                               external, nl_rel, rnd)
        hist.append(1 if u else 0)
        tot += S.score(cl, u, t['grounded'], cost, budget, penalty)
        st['spent'] += cost
        if u:
            st['unk'] += 1
            if t['grounded']:
                st['n_unk_true'] += 1
                if cl:
                    st['unk_true_recall'] += 1
            else:
                st['n_unk_hole'] += 1
                if cl:
                    st['unk_hole_pass'] += 1
        else:
            if not t['grounded'] and cl:
                st['fp'] += 1
            if t['grounded'] and not cl:
                st['fn'] += 1
    n = len(tasks)
    st['score'] = tot / n
    st['spent'] = st['spent'] / n
    if st['n_unk_true']:
        st['unk_true_recall'] /= st['n_unk_true']
    if st['n_unk_hole']:
        st['unk_hole_pass'] /= st['n_unk_hole']
    return tot / n, st


def multieval(tasks, corpus, params, seeds=(0, 1, 2), **kw):
    rs = [evaluate(tasks, corpus, params, random.Random(s), **kw)[0] for s in seeds]
    return statistics.mean(rs), statistics.stdev(rs) if len(rs) > 1 else 0.0


def learn(tasks_list, corpus, seeds=(0, 1, 2), start=None, rounds=3, no_beta=False):
    """坐标下降：在多个环境上共同学一组参数。

    no_beta=True 时固定 beta=0 —— 即"只记住一个固定门槛"的记忆派，
    它无法随环境调节，这正是要和"学规则"对照的东西。
    """
    p = dict(start or {'d': 6, 'tau': 0.5, 'thr0': 0.5, 'beta': 0.0})
    best = None
    bgrid = [0.0] if no_beta else BETA_GRID
    for _ in range(rounds):
        for key, grid in (('d', D_GRID), ('tau', TAU_GRID),
                          ('thr0', THR_GRID), ('beta', bgrid)):
            for v in grid:
                cand = dict(p)
                cand[key] = v
                sc = statistics.mean(
                    [multieval(ts, corpus, cand, seeds)[0] for ts in tasks_list])
                if best is None or sc > best[0]:
                    best = (sc, dict(cand))
            if best:
                p = dict(best[1])
    return best[1], best[0]


def main():
    R = {}
    corpus = S.Corpus(sysconfig.get_paths()['stdlib'])
    R['corpus'] = {'files': len(corpus.files), 'defs': len(corpus.defs),
                   'calls': len(corpus.calls), 'nl_tokens': len(corpus.nl),
                   'dist_max': max(corpus.dist.values()),
                   'dist_mean': round(statistics.mean(
                       [k for k in corpus.dist.values() if k > 0]), 2)}

    rnd = random.Random(7)
    files = list(corpus.files)
    rnd.shuffle(files)
    tr_files, he_files = set(files[:len(files) // 2]), set(files[len(files) // 2:])
    tr_pool = [c for c in corpus.calls if c[1] in tr_files]
    he_pool = [c for c in corpus.calls if c[1] in he_files]

    # 训练环境：不同空洞率（她要学一条能跨环境用的规则，不是记住一个数）
    envs = []
    for hr in (0.10, 0.25, 0.40, 0.55):
        envs.append((hr, S.make_tasks(corpus, hr, 220, random.Random(100 + int(hr * 100)),
                                      pool=tr_pool)))
    train_tasks = [t for _, t in envs]
    held_tasks = S.make_tasks(corpus, 0.32, 300, random.Random(999), pool=he_pool)
    R['sizes'] = {'train_envs': len(envs), 'train_each': 220, 'held': len(held_tasks)}

    # ── 判据1 尺子自检 ────────────────────────────────────────
    r0 = random.Random(0)
    ts = envs[1][1]
    def perfect(ts):
        tot = 0.0
        for t in ts:
            tot += S.score(t['grounded'], False, t['grounded'], 0.0, BUDGET, PENALTY)
        return tot / len(ts)
    def allclaim(ts, v):
        tot = 0.0
        for t in ts:
            tot += S.score(v, False, t['grounded'], 0.0, BUDGET, PENALTY)
        return tot / len(ts)
    def randbase(ts):
        tot = 0.0
        rr = random.Random(5)
        for t in ts:
            tot += S.score(rr.random() < 0.5, False, t['grounded'], 0.0, BUDGET, PENALTY)
        return tot / len(ts)
    R['c1_ruler'] = {'perfect': perfect(ts), 'all_true': allclaim(ts, True),
                     'all_false': allclaim(ts, False), 'random': randbase(ts)}
    R['c1_pass'] = (R['c1_ruler']['perfect'] >
                    max(R['c1_ruler']['all_true'], R['c1_ruler']['all_false'],
                        R['c1_ruler']['random']) + 0.05)

    # ── 判据2 d 内部峰 ────────────────────────────────────────
    scan = {}
    for d in D_GRID:
        scan[d] = multieval(ts, corpus, {'d': d, 'tau': 0.5, 'thr': 0.5})[0]
    R['c2_d_scan'] = {str(k): round(v, 4) for k, v in scan.items()}
    bd = max(scan, key=scan.get)
    R['c2'] = {'best_d': bd, 'best': round(scan[bd], 4),
               'left': round(scan[D_GRID[0]], 4), 'right': round(scan[D_GRID[-1]], 4)}
    R['c2_pass'] = (D_GRID[0] < bd < D_GRID[-1]) and \
                   (scan[bd] > scan[D_GRID[0]] + 0.01) and \
                   (scan[bd] > scan[D_GRID[-1]] + 0.01)

    # ── 判据3 d 硬依赖：关掉成本 → 峰应到边界 ────────────────
    scan0 = {}
    for d in D_GRID:
        scan0[d] = multieval(ts, corpus, {'d': d, 'tau': 0.5, 'thr': 0.5}, penalty=0.0)[0]
    R['c3_d_scan_nopenalty'] = {str(k): round(v, 4) for k, v in scan0.items()}
    bd0 = max(scan0, key=scan0.get)
    span_on = max(scan.values()) - min(scan.values())
    span_off = max(scan0.values()) - min(scan0.values())
    # 关掉成本后 d 不再有系统地影响分数 —— 曲线塌成噪声，这才是"价值来自成本"的证据
    R['c3'] = {'best_d_off': bd0, 'span_on': round(span_on, 4),
               'span_off': round(span_off, 4),
               'right_drop_on': round(scan[bd] - scan[D_GRID[-1]], 4)}
    R['c3_pass'] = (span_off < span_on / 2.0) and (scan[bd] - scan[D_GRID[-1]] > 0.05)

    # ── 判据4 tau 内部峰 ──────────────────────────────────────
    st_scan = {}
    for tau in TAU_GRID:
        st_scan[tau] = multieval(ts, corpus, {'d': 6, 'tau': tau, 'thr': 0.5})[0]
    R['c4_tau_scan'] = {str(k): round(v, 4) for k, v in st_scan.items()}
    bt = max(st_scan, key=st_scan.get)
    R['c4'] = {'best_tau': bt, 'best': round(st_scan[bt], 4)}
    R['c4_pass'] = 0.0 < bt < 1.0

    # ── 判据5 tau 硬依赖两端：关掉 NL → 价值方向翻转 ──────────
    dep = {}
    for rel in (0.0, 1.0):
        lo = multieval(ts, corpus, {'d': 6, 'tau': 0.0, 'thr': 0.5}, nl_rel=rel)[0]
        hi = multieval(ts, corpus, {'d': 6, 'tau': 1.0, 'thr': 0.5}, nl_rel=rel)[0]
        dep[rel] = {'tau0': round(lo, 4), 'tau1': round(hi, 4), 'delta': round(hi - lo, 4)}
    R['c5_nl_dependency'] = {str(k): v for k, v in dep.items()}
    R['c5_pass'] = (dep[1.0]['delta'] > 0.02) and (dep[0.0]['delta'] < 0.0)

    # ── 判据6 thr 内部峰 ──────────────────────────────────────
    th_scan = {}
    for thr in THR_GRID:
        th_scan[thr] = multieval(ts, corpus, {'d': 6, 'tau': 0.5, 'thr': thr})[0]
    R['c6_thr_scan'] = {str(k): round(v, 4) for k, v in th_scan.items()}
    bh = max(th_scan, key=th_scan.get)
    R['c6'] = {'best_thr': bh, 'best': round(th_scan[bh], 4)}
    R['c6_pass'] = (THR_GRID[0] < bh < THR_GRID[-1])

    # ── 判据7 "追不到" ≠ "不存在" ────────────────────────────
    _, st7 = evaluate(ts, corpus, {'d': 2, 'tau': 0.5, 'thr': 0.5}, random.Random(3))
    R['c7'] = {'n_unk_true': st7['n_unk_true'], 'n_unk_hole': st7['n_unk_hole'],
               'unk_true_recall': round(st7['unk_true_recall'], 3),
               'unk_hole_pass': round(st7['unk_hole_pass'], 3)}
    R['c7_pass'] = (st7['n_unk_true'] > 5 and st7['n_unk_hole'] > 5 and
                    st7['unk_true_recall'] - st7['unk_hole_pass'] > 0.10)

    # ── 判据11 UNKNOWN 不能刷分 ──────────────────────────────
    # 极端策略：d=1 什么都追不到 + thr 极低全部放行（靠 UNKNOWN 免罚）
    evade = multieval(ts, corpus, {'d': 1, 'tau': 0.0, 'thr': 0.0})[0]
    R['c11_evade'] = round(evade, 4)
    R['c11_pass'] = evade < scan[bd] - 0.05

    # ── 学 ────────────────────────────────────────────────────
    hers, train_sc = learn(train_tasks, corpus,
                           start={'d': 6, 'tau': 0.5, 'thr0': 0.5, 'beta': 0.0})
    R['learned'] = {'params': hers, 'train_score': round(train_sc, 4)}
    R['mine'] = MINE

    # ── 判据8 跨空洞率：她 vs 记忆派 vs 我 ───────────────────
    # 记忆派：在单一空洞率(0.25)上学出的参数，硬套
    # 记忆派：只在单一空洞率上学，且不学 beta（等于记住一个固定门槛）
    memo, _ = learn([envs[1][1]], corpus,
                    start={'d': 6, 'tau': 0.5, 'thr0': 0.5, 'beta': 0.0},
                    no_beta=True)
    R['memory'] = memo
    cross = {}
    for hr in (0.15, 0.35, 0.50):
        t2 = S.make_tasks(corpus, hr, 260, random.Random(700 + int(hr * 100)), pool=he_pool)
        h = multieval(t2, corpus, hers)[0]
        m = multieval(t2, corpus, memo)[0]
        mi = multieval(t2, corpus, MINE)[0]
        cross[str(hr)] = {'hers': round(h, 4), 'memory': round(m, 4), 'mine': round(mi, 4)}
    R['c8_cross'] = cross
    R['c8_pass'] = all(v['hers'] > v['memory'] for v in cross.values())

    # ── 判据9 held-out（没见过的文件）────────────────────────
    hh, hsd = multieval(held_tasks, corpus, hers)
    hm, _ = multieval(held_tasks, corpus, memo)
    hmine, _ = multieval(held_tasks, corpus, MINE)
    rndbase = multieval(held_tasks, corpus,
                        {'d': D_GRID[0], 'tau': 0.5, 'thr': 0.5})[0]
    R['c9_held'] = {'hers': round(hh, 4), 'sd': round(hsd, 4), 'memory': round(hm, 4),
                    'mine': round(hmine, 4), 'blind': round(rndbase, 4)}
    R['c9_pass'] = hh > hm and hh > rndbase

    # ── 判据10 她赢我填的 ────────────────────────────────────
    R['c10_pass'] = hh > hmine
    R['c10_gap'] = round(hh - hmine, 4)

    # ── 判据12 空洞混入后整体下降（★88 同构）─────────────────
    pure = S.make_tasks(corpus, 0.0, 260, random.Random(555), pool=he_pool)
    mixed = S.make_tasks(corpus, 0.35, 260, random.Random(556), pool=he_pool)
    R['c12'] = {'pure': round(multieval(pure, corpus, hers)[0], 4),
                'mixed': round(multieval(mixed, corpus, hers)[0], 4)}
    R['c12_pass'] = R['c12']['mixed'] < R['c12']['pure']

    R['passed'] = sum(1 for k in R if k.endswith('_pass') and R[k])
    R['total'] = sum(1 for k in R if k.endswith('_pass'))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
