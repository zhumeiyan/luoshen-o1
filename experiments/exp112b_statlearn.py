"""★112b 统计学习 —— 加感知噪声后重测

★112 全 1.0 → 考场太干净（TP 1.00 vs 0.33，信号强到没有区分度），
判据 2/3/8 通过但没有信息量，alpha 无峰。作废。

真实的婴儿/她的听觉都不是完美的：听到的音节会认错。
加"音节混淆率"，把考场推到真正有难度的地方。
"""
import sys, os, json
import numpy as np

ROOT = '/data/workspace/luoshen-o1'
sys.path.insert(0, ROOT)
from core import statlearn as S

RES = {}


def rec(k, v):
    RES[k] = v
    print(f'  {k}: {v}')


class NoisyLearner(S.Learner):
    """她的输入不是完美音节序列：有一定比例被认错"""

    def __init__(self, alpha=0.5, W=None, noise=0.0, pool=None, seed=0):
        super().__init__(alpha, W)
        self.noise = float(noise)
        self.pool = pool or []
        self.seed = seed

    def fit(self, seq):
        rng = np.random.default_rng(self.seed)
        obs = list(seq)
        if self.noise > 0 and self.pool:
            for i in range(len(obs)):
                if rng.random() < self.noise:
                    obs[i] = self.pool[int(rng.integers(0, len(self.pool)))]
        return super().fit(obs)


def forced_choice(learner, A_list, B_list):
    hit = n = 0
    for a in A_list:
        for b in B_list:
            sa, sb = learner.score(a), learner.score(b)
            hit += 1 if sa > sb else (0.5 if abs(sa - sb) < 1e-15 else 0)
            n += 1
    return hit / max(n, 1)


def tp_struct(learner, words):
    L = len(words[0])
    ins = [learner._p(w[i], w[i + 1]) for w in words for i in range(L - 1)]
    bnd = [learner._p(w1[-1], w2[0]) for w1 in words for w2 in words
           if tuple(w1) != tuple(w2)]
    return float(np.mean(ins)), float(np.mean(bnd))


def main():
    syls, nchar, _ = S.real_syllables(60)
    rec('real_hanzi', nchar)

    words, _ = None, None
    rng0 = np.random.default_rng(0)
    words = S.make_words(syls, 4, 3, rng0)
    rec('words', [' '.join(w) for w in words])
    pool = [s for w in words for s in w]
    wl, parts, nonwords = S.test_items(words, np.random.default_rng(3))
    stream = S.make_stream(words, 40, np.random.default_rng(7))

    print('\n【A】噪声扫描：把考场推到有难度的地方')
    curve = {}
    for nz in (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40):
        accs = []
        for sd in range(6):
            L = NoisyLearner(alpha=0.5, noise=nz, pool=pool,
                             seed=1000 + sd).fit(stream)
            accs.append(forced_choice(L, wl, parts))
        m = float(np.mean(accs))
        se = float(np.std(accs) / np.sqrt(len(accs)))
        curve[nz] = m
        rec(f'acc_noise{nz}', f'{m:.4f} ± {2*se:.4f}')
    # 选一个「有难度但仍可学」的水平：正确率落在 0.65~0.85
    cand = [k for k, v in curve.items() if 0.62 <= v <= 0.88]
    target = max(cand) if cand else (max(curve, key=lambda k: k) if curve else 0.2)
    rec('chosen_noise', target)
    rec('acc_at_chosen', round(curve[target], 4))

    print('\n【B】在真实难度下：平滑先验 alpha 有内部峰吗')
    best = (None, -1)
    row = {}
    for al in (0.05, 0.1, 0.2, 0.4, 0.8, 1.5, 3.0, 6.0):
        accs = []
        for sd in range(6):
            L = NoisyLearner(alpha=al, noise=target, pool=pool,
                             seed=1000 + sd).fit(stream)
            accs.append(forced_choice(L, wl, parts))
        m = float(np.mean(accs))
        row[al] = m
        rec(f'acc_alpha{al}', round(m, 4))
        if m > best[1]:
            best = (al, m)
    lo, hi = min(row, key=lambda k: k), max(row, key=lambda k: k)
    rec('alpha_peak', best[0])
    rec('alpha_span', round(max(row.values()) - min(row.values()), 4))
    rec('alpha_is_interior', bool(lo < best[0] < hi))

    print('\n【C】在真实难度下：频次控制还成立吗')
    L = NoisyLearner(alpha=best[0], noise=target, pool=pool, seed=1000).fit(stream)
    rec('acc_word_vs_nonword', round(forced_choice(L, wl, nonwords[:12]), 4))
    rec('acc_word_vs_partword', round(forced_choice(L, wl, parts), 4))

    print('\n【D】在真实难度下：暴露时长')
    for rep in (5, 10, 20, 40, 80, 160):
        st = S.make_stream(words, rep, np.random.default_rng(7))
        accs = [forced_choice(NoisyLearner(alpha=best[0], noise=target,
                                           pool=pool, seed=1000 + sd).fit(st),
                              wl, parts) for sd in range(6)]
        rec(f'acc_rep{rep}', round(float(np.mean(accs)), 4))

    print('\n【E】在真实难度下：记忆窗口 W（流结构切换）')
    words2 = S.make_words(syls[12:24], 4, 3, np.random.default_rng(11))
    rec('words_phase2', [' '.join(w) for w in words2])
    pool2 = [s for w in words2 for s in w]
    wl2, parts2, _ = S.test_items(words2, np.random.default_rng(4))
    st_sw = (S.make_stream(words, 30, np.random.default_rng(7))
             + S.make_stream(words2, 30, np.random.default_rng(8)))
    bestW, rowW = (None, -1), {}
    for W in (30, 60, 120, 240, 480, 960, None):
        accs = [forced_choice(NoisyLearner(alpha=best[0], W=W, noise=target,
                                           pool=pool + pool2,
                                           seed=1000 + sd).fit(st_sw),
                              wl2, parts2) for sd in range(6)]
        m = float(np.mean(accs))
        rowW[W] = m
        rec(f'acc_W{W}', round(m, 4))
        if m > bestW[1]:
            bestW = (W, m)
    rec('W_peak', bestW[0])
    rec('W_span', round(max(rowW.values()) - min(rowW.values()), 4))
    rec('W_is_interior', bool(bestW[0] not in (30, None)))

    print('\n【F】在真实难度下：硬依赖（打碎 TP）')
    rnd = np.random.default_rng(9)
    flat = [pool[int(i)] for i in rnd.integers(0, len(pool), len(stream))]
    accs = [forced_choice(NoisyLearner(alpha=best[0], noise=target, pool=pool,
                                       seed=1000 + sd).fit(flat),
                          wl, parts) for sd in range(6)]
    a_f = float(np.mean(accs))
    rec('acc_flat', round(a_f, 4))
    rec('hard_dependence', round(curve[target] - a_f, 4))

    json.dump(RES, open(f'{ROOT}/data/exp112b_statlearn.json', 'w'),
              ensure_ascii=False, indent=1)
    print('\n→ data/exp112b_statlearn.json')


if __name__ == '__main__':
    main()
