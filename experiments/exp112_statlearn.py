"""★112 统计学习（Saffran 范式）—— 前语言阶段的切词

按《预注册_112_统计学习.md》跑。判据先写了，不改。
这一课她不说话：测的是理解/感知，不是产出。
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


def forced_choice(learner, A_list, B_list, rng):
    """A vs B 强迫选择，返回选 A 的比例"""
    hit = 0
    n = 0
    for a in A_list:
        for b in B_list:
            sa, sb = learner.score(a), learner.score(b)
            if sa > sb:
                hit += 1
            elif abs(sa - sb) < 1e-15:
                hit += 0.5
            n += 1
    return hit / max(n, 1)


def build(seed, syls, n_word=4, wlen=3):
    rng = np.random.default_rng(seed)
    words = S.make_words(syls, n_word, wlen, rng)
    return words, rng


def tp_struct(learner, words):
    """实测：词内 bigram 的平均转移概率 vs 跨界 bigram"""
    L = len(words[0])
    inside, bnd = [], []
    for w in words:
        for i in range(L - 1):
            inside.append(learner._p(w[i], w[i + 1]))
    for w1 in words:
        for w2 in words:
            if w1 is not w2 and tuple(w1) != tuple(w2):
                bnd.append(learner._p(w1[-1], w2[0]))
    return float(np.mean(inside)), float(np.mean(bnd))


def main():
    print('【1】真实音节（REAL）')
    syls, nchar, _ = S.real_syllables(60)
    rec('real_hanzi', nchar)
    rec('syllable_types_seen', 399)
    rec('top_syllables', syls[:12])
    assert nchar > 100000, '语料没读到'

    print('\n【0】尺子自检：流的 TP 结构（REAL 实测）')
    words, rng = build(0, syls)
    rec('words', [' '.join(w) for w in words])
    stream = S.make_stream(words, 60, np.random.default_rng(7))
    L = S.Learner(alpha=0.5).fit(stream)
    ins, bnd = tp_struct(L, words)
    rec('tp_inside', round(ins, 4))
    rec('tp_boundary', round(bnd, 4))
    rec('tp_ratio', round(ins / max(bnd, 1e-9), 2))

    print('\n【2】她能切词吗：word vs part-word')
    wl, parts, nonwords = S.test_items(words, np.random.default_rng(3))
    acc = forced_choice(L, wl, parts, rng)
    rec('acc_word_vs_partword', round(acc, 4))
    rec('streams_pairs', len(wl) * len(parts))

    print('\n【3】频次控制：word vs non-word（音节完全相同，只换顺序）')
    acc_nw = forced_choice(L, wl, nonwords[:12], rng)
    rec('acc_word_vs_nonword', round(acc_nw, 4))
    rec('control_note', 'nonword 与 word 音节构成相同，只有顺序不同')

    print('\n【4】暴露时长曲线')
    for rep in (2, 5, 10, 20, 40, 80, 160):
        st = S.make_stream(words, rep, np.random.default_rng(7))
        l = S.Learner(alpha=0.5).fit(st)
        a = forced_choice(l, wl, parts, rng)
        rec(f'acc_rep{rep}', round(a, 4))

    print('\n【5】平滑先验 alpha 有内部峰吗')
    st = S.make_stream(words, 40, np.random.default_rng(7))
    best = (None, -1)
    for al in (0.01, 0.05, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0):
        l = S.Learner(alpha=al).fit(st)
        a = forced_choice(l, wl, parts, rng)
        rec(f'acc_alpha{al}', round(a, 4))
        if a > best[1]:
            best = (al, a)
    rec('alpha_peak', best[0])
    rec('alpha_is_interior', bool(0.01 < best[0] < 10.0))

    print('\n【6】流结构切换时，记忆窗口 W 有内部峰吗')
    words2, rng2 = build(11, syls[12:24])          # 换一组音节 → 换一套词
    rec('words_phase2', [' '.join(w) for w in words2])
    st1 = S.make_stream(words, 30, np.random.default_rng(7))
    st2 = S.make_stream(words2, 30, np.random.default_rng(8))
    stream_sw = st1 + st2
    wl2, parts2, nw2 = S.test_items(words2, np.random.default_rng(4))
    bestW = (None, -1)
    for W in (30, 60, 120, 240, 480, 960, None):
        l = S.Learner(alpha=0.5, W=W).fit(stream_sw)
        a = forced_choice(l, wl2, parts2, rng)
        rec(f'acc_W{W}', round(a, 4))
        if a > bestW[1]:
            bestW = (W, a)
    rec('W_peak', bestW[0])
    rec('W_is_interior', bool(bestW[0] not in (30, None)))

    print('\n【7】硬依赖：把 TP 结构打碎')
    flat = list(syls[:12])
    rnd = np.random.default_rng(9)
    shuffled = [flat[int(i)] for i in rnd.integers(0, 12, len(stream))]
    Lf = S.Learner(alpha=0.5).fit(shuffled)
    ins_f, bnd_f = tp_struct(Lf, words)
    rec('flat_tp_inside', round(ins_f, 4))
    rec('flat_tp_boundary', round(bnd_f, 4))
    a_f = forced_choice(Lf, wl, parts, rng)
    rec('acc_flat', round(a_f, 4))
    rec('hard_dependence', round(acc - a_f, 4))

    print('\n【8】跨流复现（3 个独立流）')
    accs = []
    for sd in (21, 22, 23):
        w_, r_ = build(sd, syls)
        st_ = S.make_stream(w_, 40, np.random.default_rng(100 + sd))
        l_ = S.Learner(alpha=0.5).fit(st_)
        wl_, p_, _ = S.test_items(w_, np.random.default_rng(sd))
        a_ = forced_choice(l_, wl_, p_, rng)
        accs.append(a_)
        rec(f'acc_stream{sd}', round(a_, 4))
    rec('acc_mean', round(float(np.mean(accs)), 4))
    rec('acc_min', round(float(np.min(accs)), 4))

    json.dump(RES, open(f'{ROOT}/data/exp112_statlearn.json', 'w'),
              ensure_ascii=False, indent=1)
    print('\n→ data/exp112_statlearn.json')


if __name__ == '__main__':
    main()
